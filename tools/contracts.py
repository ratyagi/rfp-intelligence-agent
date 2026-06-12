"""Pydantic contracts for the six-stage pipeline.

Two kinds of models live here:

1. Per-call models (LLM output shapes) — what a single chat_json() call must
   return. Pass these to chat_json(schema=...) and the client retries once on
   schema-invalid output, feeding the validation error back to the model.

2. Inter-stage contracts — the data each stage hands to the next
   (RequirementManifest, EvidenceMap, ScoredManifest, DraftedProposal,
   VerifiedProposal). The orchestrator validates these between stages so a
   malformed payload fails loudly at the boundary instead of deep inside a
   later stage.

Soft vocabulary fields (priority, category) coerce unknown values to their
defaults instead of failing — a vocab slip should not burn a retry or kill a
stage. Structural fields (ids, scores, required text) stay strict.
"""
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator

Priority = Literal["high", "medium", "low"]
Category = Literal["technical", "commercial", "legal", "timeline", "team", "references", "other"]
ScoreLabel = Literal["COVERED", "PARTIAL", "GAP"]

_PRIORITIES = {"high", "medium", "low"}
_CATEGORIES = {"technical", "commercial", "legal", "timeline", "team", "references", "other"}


class _Base(BaseModel):
    """Ignore extra keys — models may add fields we don't contract on."""
    model_config = ConfigDict(extra="ignore")


class _SoftVocabMixin(BaseModel):
    @field_validator("priority", mode="before", check_fields=False)
    @classmethod
    def _coerce_priority(cls, v: object) -> str:
        v = str(v).lower().strip() if v is not None else ""
        return v if v in _PRIORITIES else "medium"

    @field_validator("category", mode="before", check_fields=False)
    @classmethod
    def _coerce_category(cls, v: object) -> str:
        v = str(v).lower().strip() if v is not None else ""
        return v if v in _CATEGORIES else "other"


# ── Per-call LLM output models ───────────────────────────────────────────────

class ExtractedRequirement(_Base, _SoftVocabMixin):
    """One requirement as the Intake model returns it (id is renumbered later)."""
    id: str = ""
    text: str = Field(min_length=1)
    priority: Priority = "medium"
    category: Category = "other"


class IntakeExtraction(_Base):
    """Output contract for one Intake extraction call (one chunk of sections)."""
    requirements: list[ExtractedRequirement] = []


class ScoreJudgement(_Base):
    """Output contract for one Scorer call (one requirement)."""
    score: ScoreLabel
    confidence: float = 0.5
    gap_note: Optional[str] = None

    @field_validator("confidence", mode="before")
    @classmethod
    def _clamp_confidence(cls, v: object) -> float:
        try:
            return min(1.0, max(0.0, float(v)))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0.5


class DraftedSection(_Base):
    """Output contract for one Drafter call (one requirement)."""
    req_id: str = ""
    response_text: str = Field(min_length=1)
    evidence_citations: Optional[str] = None


# ── Inter-stage contracts ────────────────────────────────────────────────────

class Requirement(_Base, _SoftVocabMixin):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    priority: Priority = "medium"
    category: Category = "other"


class RequirementManifest(_Base):
    """Stage 1 (Intake) → Stage 2 (Research)."""
    requirements: list[Requirement]


class EvidenceItem(_Base):
    doc_id: str = Field(min_length=1)
    title: str = ""
    excerpt: str = ""
    source_path: str = ""
    score: float = 0.0


class EvidenceMap(RootModel[dict[str, list[EvidenceItem]]]):
    """Stage 2 (Research) → Stages 3-6. Keyed by requirement id; an empty
    list is a finding (no corpus coverage), not an error."""


class GapAction(_Base):
    id: str
    gap_note: str


class ScoredRequirement(_Base, _SoftVocabMixin):
    id: str = Field(min_length=1)
    score: ScoreLabel
    confidence: float = 0.5
    gap_note: Optional[str] = None
    # Enriched by the orchestrator before drafting; absent straight after scoring.
    text: str = ""
    priority: Priority = "medium"
    category: Category = "other"


class ScoredManifest(_Base):
    """Stage 3 (Scorer) → Stage 4 (Drafter)."""
    scored_requirements: list[ScoredRequirement]
    win_probability: Optional[int] = None
    gap_count: int = 0
    gaps_requiring_action: list[GapAction] = []


class RequirementVerification(_Base):
    cited: list[str] = []
    verified: list[str] = []
    stripped: list[str] = []


class DraftedRequirement(_Base, _SoftVocabMixin):
    id: str = Field(min_length=1)
    text: str = ""
    priority: Priority = "medium"
    category: Category = "other"
    confidence: Optional[float] = None
    score: ScoreLabel
    response_text: Optional[str] = None
    evidence_citations: Optional[str] = None
    gap_note: Optional[str] = None
    verification: Optional[RequirementVerification] = None


class DraftedProposal(_Base):
    """Stage 4 (Drafter) → Stage 5 (Verifier)."""
    company_name: str
    rfp_title: str
    submission_date: str
    executive_summary: str
    win_probability: Optional[int] = None
    requirements: list[DraftedRequirement]


class VerificationFlag(_Base):
    id: str
    stripped_citations: list[str] = []
    note: str = ""


class VerificationSummary(_Base):
    citations_total: int
    citations_verified: int
    citations_stripped: int
    flags: list[VerificationFlag] = []


class VerifiedProposal(DraftedProposal):
    """Stage 5 (Verifier) → Stage 6 (Review)."""
    gap_count: int = 0
    verification: VerificationSummary
