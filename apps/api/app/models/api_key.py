"""
API Key Pydantic models.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

# Scopes valides. Granularité : `{resource}:{action}`. `*` = wildcard admin.
# Une API key `workspaces:write` peut créer/modifier des workspaces mais pas toucher au chat.
VALID_SCOPES: frozenset[str] = frozenset(
    {
        "*",
        "workspaces:read",
        "workspaces:write",
        "sources:read",
        "sources:write",
        "chat:read",
        "chat:write",
        "insights:read",
        "insights:write",
        "investigations:read",
        "investigations:write",
        "deliverables:read",
        "deliverables:write",
        "notes:read",
        "notes:write",
    }
)


def _validate_scopes(scopes: list[str]) -> list[str]:
    invalid = [s for s in scopes if s not in VALID_SCOPES]
    if invalid:
        raise ValueError(
            f"Invalid scope(s): {', '.join(invalid)}. "
            f"Allowed: {', '.join(sorted(VALID_SCOPES))}"
        )
    return scopes


class ApiKeyCreate(BaseModel):
    """Body for creating a new API key."""

    name: str = Field(..., min_length=1, max_length=100)
    scopes: list[str] = Field(default=["*"])
    rpm_limit: int = Field(default=60, ge=1, le=10000)
    rpd_limit: int = Field(default=1000, ge=1, le=100000)

    @field_validator("scopes")
    @classmethod
    def _check_scopes(cls, v: list[str]) -> list[str]:
        return _validate_scopes(v)


class ApiKeyUpdate(BaseModel):
    """Body for updating API key metadata."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    scopes: list[str] | None = None
    rpm_limit: int | None = Field(default=None, ge=1, le=10000)
    rpd_limit: int | None = Field(default=None, ge=1, le=100000)
    is_active: bool | None = None

    @field_validator("scopes")
    @classmethod
    def _check_scopes(cls, v: list[str] | None) -> list[str] | None:
        return _validate_scopes(v) if v is not None else None


class ApiKeyResponse(BaseModel):
    """API key response — NEVER includes the secret."""

    id: str
    name: str
    key_prefix: str
    scopes: list[str]
    rpm_limit: int
    rpd_limit: int
    is_active: bool
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    created_by: str
    created_at: datetime


class ApiKeyCreated(BaseModel):
    """Response after create or rotate — includes secret ONE TIME ONLY."""

    id: str
    name: str
    key: str  # xv_live_{32_hex} — shown once, never stored
    key_prefix: str
    scopes: list[str]
    rpm_limit: int
    rpd_limit: int
    is_active: bool
    created_at: datetime


class ApiKeyWithUsage(ApiKeyResponse):
    """Detail response with usage stats."""

    usage_today: int = 0
    usage_this_month: int = 0
