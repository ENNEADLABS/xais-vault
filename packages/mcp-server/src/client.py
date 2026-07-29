"""HTTP client for XAIS Vault API."""

import json

import httpx


class VaultAPIError(Exception):
    """Levée quand l'API retourne une erreur."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"API error {status_code}: {message}")


class VaultClient:
    """Client HTTP async pour l'API XAIS Vault.

    Usage:
        async with VaultClient(base_url="...", api_key="...") as client:
            workspaces = await client.list_workspaces()
    """

    def __init__(self, *, base_url: str, api_key: str):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._http: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self._http = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "X-API-Key": self._api_key,
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(30.0, read=120.0),
        )
        return self

    async def __aexit__(self, *args):
        if self._http:
            await self._http.aclose()

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        """Handler unifié avec parsing d'erreurs."""
        response = await self._http.request(method, f"/api/v2{path}", **kwargs)
        if response.status_code >= 400:
            body = response.json()
            error = body.get("error", {})
            message = error.get("message", response.text)
            raise VaultAPIError(response.status_code, message)
        if response.status_code == 204:
            return {}
        return response.json()

    # ─── Workspaces ─────────────────────────────────────────────

    async def list_workspaces(self, status: str | None = None) -> dict:
        params = {}
        if status:
            params["status"] = status
        return await self._request("GET", "/workspaces", params=params)

    async def get_workspace(self, workspace_id: str) -> dict:
        return await self._request("GET", f"/workspaces/{workspace_id}")

    async def create_workspace(self, name: str, **kwargs) -> dict:
        body = {"name": name, **kwargs}
        return await self._request("POST", "/workspaces", json=body)

    # ─── Sources ───────────────────────────────────────────

    async def list_sources(self, workspace_id: str) -> dict:
        return await self._request("GET", f"/workspaces/{workspace_id}/sources")

    async def upload_text_source(
        self, workspace_id: str, name: str, content: str,
    ) -> dict:
        return await self._request(
            "POST",
            f"/workspaces/{workspace_id}/sources/text",
            json={"name": name, "content": content},
        )

    # ─── Chat ──────────────────────────────────────────────

    async def chat(
        self, workspace_id: str, content: str, session_id: str | None = None,
    ) -> dict:
        """Envoie un message chat. NON-streaming — attend la réponse complète.

        L'API retourne du SSE. Ce client consomme le stream SSE et reconstruit
        la réponse (texte + citations + usage) avant de retourner.
        """
        body: dict = {"content": content}
        if session_id:
            body["session_id"] = session_id

        response = await self._http.request(
            "POST",
            f"/api/v2/workspaces/{workspace_id}/chat",
            json=body,
        )
        if response.status_code >= 400:
            raise VaultAPIError(response.status_code, response.text)

        return self._parse_sse_response(response.text)

    @staticmethod
    def _parse_sse_response(raw: str) -> dict:
        """Parse un event stream SSE en un dict de réponse unique."""
        result: dict = {
            "session_id": None,
            "content": "",
            "citations": [],
            "usage": {},
        }
        current_event = ""
        for line in raw.split("\n"):
            if line.startswith("event: "):
                current_event = line[7:]
            elif line.startswith("data: "):
                data = json.loads(line[6:])
                if current_event == "session":
                    result["session_id"] = data.get("id")
                elif current_event == "content":
                    result["content"] += data.get("text", "")
                elif current_event == "citations":
                    result["citations"] = data.get("citations", [])
                elif current_event == "usage":
                    result["usage"] = data
        return result

    # ─── Insights ──────────────────────────────────────────

    async def list_insights(
        self,
        workspace_id: str,
        *,
        type: str | None = None,
        severity: str | None = None,
        status: str | None = None,
    ) -> dict:
        params = {}
        if type:
            params["type"] = type
        if severity:
            params["severity"] = severity
        if status:
            params["status"] = status
        return await self._request(
            "GET", f"/workspaces/{workspace_id}/insights", params=params,
        )

    async def investigate_insight(
        self, workspace_id: str, insight_id: str,
    ) -> dict:
        return await self._request(
            "PATCH",
            f"/workspaces/{workspace_id}/insights/{insight_id}",
            json={"action": "investigate"},
        )

    # ─── Investigations ────────────────────────────────────

    async def list_investigations(
        self,
        workspace_id: str,
        *,
        status: str | None = None,
        insight_id: str | None = None,
    ) -> dict:
        params = {}
        if status:
            params["status"] = status
        if insight_id:
            params["insight_id"] = insight_id
        return await self._request(
            "GET", f"/workspaces/{workspace_id}/investigations", params=params,
        )

    # ─── Deliverables ──────────────────────────────────────

    async def generate_deliverable(
        self,
        workspace_id: str,
        type: str,
        name: str,
        options: dict | None = None,
    ) -> dict:
        body: dict = {"type": type, "name": name}
        if options:
            body["options"] = options
        return await self._request(
            "POST", f"/workspaces/{workspace_id}/deliverables", json=body,
        )
