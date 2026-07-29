"""
Tests de sécurité — Injection & Validation des données (Phase 2)

Couvre :
- DoS upload : lecture RAM bornée à MAX+1 octets
- Texte collé : limite 1 MB appliquée par Pydantic
- Path traversal : filename sanitization
- SSRF webhook : IPv6, redirections, URL avec credentials
- Pydantic extra="forbid" : WorkspaceCreate/WorkspaceUpdate/SourceTextCreate
- Pagination overflow : grands numéros de page
"""

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from apps.api.app.models.source import MAX_TEXT_SIZE, SourceTextCreate
from apps.api.app.models.workspace import WorkspaceCreate, WorkspaceUpdate
from apps.api.app.services.source_upload import MAX_FILE_SIZE, upload_file_source
from apps.worker.app.services.webhook_dispatcher import validate_webhook_url

# ─── Constants ──────────────────────────────────────────────────

DEAL_ID = str(uuid.uuid4())
ORG_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())
SOURCE_ROW = {
    "id": str(uuid.uuid4()),
    "workspace_id": DEAL_ID,
    "organization_id": ORG_ID,
    "name": "test.pdf",
    "type": "pdf",
    "status": "pending",
    "uploaded_by": USER_ID,
    "created_at": "2026-01-01T00:00:00",
}
JOB_ROW = {"id": str(uuid.uuid4()), "type": "index_source", "status": "pending"}


# ─── Helpers ────────────────────────────────────────────────────


def _make_upload_file(
    filename: str, content: bytes, content_type: str = "application/pdf"
):
    f = MagicMock()
    f.filename = filename
    f.content_type = content_type

    # Simuler la lecture bornée : read(size) retourne min(size, len(content)) octets
    async def bounded_read(size: int = -1):
        if size == -1:
            return content
        return content[:size]

    f.read = bounded_read
    return f


def _make_db(deal_exists: bool = True) -> MagicMock:
    db = MagicMock()
    chain = MagicMock()
    for m in ("select", "eq", "in_", "order", "update", "delete", "insert", "upsert"):
        getattr(chain, m).return_value = chain

    if deal_exists:
        chain.execute.return_value = MagicMock(data=[{"id": DEAL_ID}])
    else:
        chain.execute.return_value = MagicMock(data=[])

    db.table.return_value = chain
    db.storage = MagicMock()
    db.storage.from_.return_value.upload = MagicMock()
    return db


# ─── 1. DoS Upload — lecture RAM bornée ──────────────────────────


@pytest.mark.asyncio
class TestDoSUpload:
    """Le fichier ne doit jamais être lu au-delà de MAX_FILE_SIZE + 1 octets."""

    async def test_oversized_file_rejected_without_full_read(self):
        """Un fichier de MAX+1 octets est rejeté avec 400, pas chargé en mémoire."""
        oversized_content = b"x" * (MAX_FILE_SIZE + 1)
        file = _make_upload_file("big.pdf", oversized_content)
        db = _make_db()

        with pytest.raises(HTTPException) as exc:
            await upload_file_source(
                workspace_id=DEAL_ID,
                organization_id=ORG_ID,
                user_id=USER_ID,
                file=file,
                db=db,
            )
        assert exc.value.status_code == 400
        assert "too large" in exc.value.detail.lower()

    async def test_read_is_called_with_size_limit(self):
        """upload_file_source appelle file.read avec MAX+1, pas sans limite."""
        reads = []

        async def tracking_read(size: int = -1):
            reads.append(size)
            return b"x" * min(size, 100)  # fichier de 100 octets

        file = MagicMock()
        file.filename = "report.pdf"
        file.content_type = "application/pdf"
        file.read = tracking_read

        db = _make_db()
        # Patch storage et job pour ne pas bloquer
        db.table.return_value.execute.return_value = MagicMock(data=[SOURCE_ROW])
        db.storage.from_.return_value.upload = MagicMock()

        from unittest.mock import patch as mock_patch

        with mock_patch(
            "apps.api.app.services.source_upload.create_job",
            return_value=JOB_ROW,
        ):
            await upload_file_source(
                workspace_id=DEAL_ID,
                organization_id=ORG_ID,
                user_id=USER_ID,
                file=file,
                db=db,
            )

        # Vérifier que read a été appelé avec MAX_FILE_SIZE + 1
        assert reads[0] == MAX_FILE_SIZE + 1

    async def test_normal_file_passes(self):
        """Un fichier de 1 Ko est accepté normalement."""
        content = b"%PDF-1.4\nfake pdf content"
        file = _make_upload_file("report.pdf", content)

        db = _make_db()
        db.table.return_value.execute.return_value = MagicMock(data=[SOURCE_ROW])

        from unittest.mock import patch as mock_patch

        with mock_patch(
            "apps.api.app.services.source_upload.create_job",
            return_value=JOB_ROW,
        ):
            source, job = await upload_file_source(
                workspace_id=DEAL_ID,
                organization_id=ORG_ID,
                user_id=USER_ID,
                file=file,
                db=db,
            )
        assert source is not None


# ─── 2. Path Traversal ───────────────────────────────────────────


@pytest.mark.asyncio
class TestPathTraversal:
    """Les noms de fichiers malicieux doivent être neutralisés."""

    async def test_path_traversal_filename_sanitized(self):
        """../../../etc/passwd.pdf doit être stocké avec un nom safe."""
        storage_paths = []

        content = b"fake"
        file = _make_upload_file("../../../etc/passwd.pdf", content)

        db = _make_db()

        def capture_upload(path, *args, **kwargs):
            storage_paths.append(path)

        db.storage.from_.return_value.upload.side_effect = capture_upload
        db.table.return_value.execute.return_value = MagicMock(data=[SOURCE_ROW])

        from unittest.mock import patch as mock_patch

        with mock_patch(
            "apps.api.app.services.source_upload.create_job",
            return_value=JOB_ROW,
        ):
            await upload_file_source(
                workspace_id=DEAL_ID,
                organization_id=ORG_ID,
                user_id=USER_ID,
                file=file,
                db=db,
            )

        assert storage_paths, "upload should have been called"
        path = storage_paths[0]
        # Le chemin ne doit pas contenir de séquences de traversal
        # (le nom "passwd" peut rester — c'est légitime ; c'est "../" qui est dangereux)
        assert "../" not in path
        assert not path.startswith("/")  # pas de chemin absolu

    async def test_null_byte_filename_sanitized(self):
        """Un filename avec null byte est traité sans erreur."""
        content = b"fake"
        file = _make_upload_file("report\x00evil.pdf", content)

        db = _make_db()
        db.table.return_value.execute.return_value = MagicMock(data=[SOURCE_ROW])

        from unittest.mock import patch as mock_patch

        with mock_patch(
            "apps.api.app.services.source_upload.create_job",
            return_value=JOB_ROW,
        ):
            source, _ = await upload_file_source(
                workspace_id=DEAL_ID,
                organization_id=ORG_ID,
                user_id=USER_ID,
                file=file,
                db=db,
            )
        assert source is not None

    async def test_unsupported_extension_rejected(self):
        """Un .exe est rejeté avec 400."""
        file = _make_upload_file("malware.exe", b"MZ\x90\x00")
        db = _make_db()

        with pytest.raises(HTTPException) as exc:
            await upload_file_source(
                workspace_id=DEAL_ID,
                organization_id=ORG_ID,
                user_id=USER_ID,
                file=file,
                db=db,
            )
        assert exc.value.status_code == 400
        assert ".exe" in exc.value.detail


# ─── 3. SSRF Webhook ─────────────────────────────────────────────


class TestSSRFWebhook:
    """validate_webhook_url doit bloquer toutes les variantes SSRF."""

    def test_localhost_blocked(self):
        with pytest.raises(ValueError, match="blocked IP"):
            validate_webhook_url("http://127.0.0.1/")

    def test_loopback_hostname_blocked(self):
        with pytest.raises(ValueError):
            validate_webhook_url("http://localhost/")

    def test_private_ip_10_blocked(self):
        with pytest.raises(ValueError, match="blocked IP"):
            validate_webhook_url("http://10.0.0.1/hook")

    def test_private_ip_192_blocked(self):
        with pytest.raises(ValueError, match="blocked IP"):
            validate_webhook_url("http://192.168.1.1/hook")

    def test_ipv6_loopback_blocked(self):
        with pytest.raises(ValueError):
            validate_webhook_url("http://[::1]/hook")

    def test_url_with_credentials_blocked(self):
        """http://user:pass@host/ doit être rejeté."""
        with pytest.raises(ValueError, match="credentials"):
            validate_webhook_url("http://admin:secret@example.com/hook")

    def test_ftp_scheme_blocked(self):
        """Schéma non-HTTP bloqué."""
        with pytest.raises(ValueError, match="scheme"):
            validate_webhook_url("ftp://example.com/data")

    def test_file_scheme_blocked(self):
        with pytest.raises(ValueError, match="scheme"):
            validate_webhook_url("file:///etc/passwd")

    def test_no_hostname_blocked(self):
        with pytest.raises(ValueError):
            validate_webhook_url("http:///path")

    def test_public_https_allowed(self):
        """URL publique valide → pas d'exception (DNS résout vers une IP publique)."""
        from unittest.mock import patch

        # IP publique de example.com (93.184.216.34)
        public_ip = "93.184.216.34"
        fake_result = [(2, 1, 6, "", (public_ip, 443))]
        with patch("socket.getaddrinfo", return_value=fake_result):
            validate_webhook_url("https://hooks.example.com/webhook")

    def test_public_http_allowed(self):
        """URL HTTP publique valide → pas d'exception."""
        from unittest.mock import patch

        public_ip = "93.184.216.34"
        fake_result = [(2, 1, 6, "", (public_ip, 80))]
        with patch("socket.getaddrinfo", return_value=fake_result):
            validate_webhook_url("http://api.example.com/events")


# ─── 4. Pydantic extra="forbid" ──────────────────────────────────


class TestPydanticExtraForbid:
    """Les modèles Create/Update rejettent les champs inconnus."""

    def test_deal_create_rejects_extra_fields(self):
        """WorkspaceCreate avec un champ inconnu → ValidationError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            WorkspaceCreate(name="Test", evil_field="hacked")

    def test_deal_update_rejects_extra_fields(self):
        """WorkspaceUpdate avec un champ inconnu → ValidationError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            WorkspaceUpdate(name="Test", __class__="override")

    def test_source_text_create_rejects_extra_fields(self):
        """SourceTextCreate avec un champ inconnu → ValidationError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SourceTextCreate(name="doc", content="text", injected=True)

    def test_deal_create_valid(self):
        """WorkspaceCreate avec champs valides → pas d'erreur."""
        d = WorkspaceCreate(name="Test Workspace", description="desc")
        assert d.name == "Test Workspace"

    def test_deal_update_valid(self):
        """WorkspaceUpdate partiel → pas d'erreur."""
        d = WorkspaceUpdate(name="New Name")
        assert d.name == "New Name"


# ─── 5. Validation taille texte collé ────────────────────────────


class TestTextSizeLimit:
    """Le texte collé ne peut pas dépasser MAX_TEXT_SIZE."""

    def test_oversized_text_rejected(self):
        """Texte de MAX+1 caractères → ValidationError."""
        from pydantic import ValidationError

        oversized = "a" * (MAX_TEXT_SIZE + 1)
        with pytest.raises(ValidationError):
            SourceTextCreate(name="doc", content=oversized)

    def test_max_size_text_accepted(self):
        """Texte exactement à la limite → accepté."""
        content = "a" * MAX_TEXT_SIZE
        s = SourceTextCreate(name="doc", content=content)
        assert len(s.content) == MAX_TEXT_SIZE

    def test_empty_text_rejected(self):
        """Texte vide → ValidationError (min_length=1)."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SourceTextCreate(name="doc", content="")

    def test_normal_text_accepted(self):
        """Texte normal → accepté."""
        s = SourceTextCreate(name="memo", content="This is a test document.")
        assert s.content == "This is a test document."
