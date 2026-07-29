"""Pydantic models for structured agent responses."""

from pydantic import BaseModel, Field, field_validator

# ─── Scanner ──────────────────────────────────────


class ScanInsight(BaseModel):
    type: str = "observation"
    severity: str = "medium"
    confidence_score: int = Field(default=50)
    title: str
    description: str
    source_id: str | None = None
    source_page: int | None = None
    source_section: str | None = None
    source_quote: str | None = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        valid = {"red_flag", "metric", "observation", "missing_info"}
        return v if v in valid else "observation"

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        valid = {"critical", "high", "medium", "low"}
        return v if v in valid else "medium"

    @field_validator("confidence_score", mode="before")
    @classmethod
    def normalize_confidence(cls, v: object) -> int:
        try:
            v_int = int(v)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 50
        return v_int if 0 <= v_int <= 100 else 50

    @field_validator("title")
    @classmethod
    def truncate_title(cls, v: str) -> str:
        return v[:500] if len(v) > 500 else v

    @field_validator("source_quote")
    @classmethod
    def truncate_quote(cls, v: str | None) -> str | None:
        if v and len(v) > 500:
            return v[:500]
        return v or None


class ScanSummary(BaseModel):
    total_insights: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    deal_risk_score: int = Field(default=0, ge=0, le=100)
    key_observation: str = ""


class ScanResponse(BaseModel):
    insights: list[ScanInsight] = Field(default_factory=list)
    summary: ScanSummary = Field(default_factory=ScanSummary)


# ─── Verifier ──────────────────────────────────────


class VerificationEvidence(BaseModel):
    source_id: str | None = None
    page: int | None = None
    quote: str = ""
    supports_insight: bool = True

    @field_validator("quote")
    @classmethod
    def truncate_quote(cls, v: str) -> str:
        return v[:300] if len(v) > 300 else v


class VerificationResponse(BaseModel):
    verdict: str = "inconclusive"
    evidence: list[VerificationEvidence] = Field(default_factory=list)
    explanation: str = ""

    @field_validator("verdict")
    @classmethod
    def validate_verdict(cls, v: str) -> str:
        valid = {"confirmed", "contradicted", "inconclusive", "nuanced"}
        return v if v in valid else "inconclusive"
