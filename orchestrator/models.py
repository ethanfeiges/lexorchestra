"""Data models for orchestration runs."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


class Claim(BaseModel):
    """A single citation-backed statement from an LLM subagent."""

    statement: str
    clause_id: str
    quote: str
    document_id: str | None = None
    sot_label: str | None = None
    rule_id: str | None = None
    verdict: str | None = None


class VerifiedClaim(BaseModel):
    """A claim after canonical grounding verification."""

    claim: Claim
    status: str
    reason: str | None = None
    model: str
    task: str
    decoy_match: str | None = None
    cross_document_match: str | None = None
    expected_document_id: str | None = None


class RunMetrics(BaseModel):
    """Aggregated metrics for one orchestration run."""

    grounding_rate: float
    decoy_citation_rate: float
    task_accuracy: float
    total_claims: int
    grounded_claims: int
    decoy_citations: int
    correct_tasks: int
    total_tasks: int
    source_fidelity: float | None = None
    decoy_probe_match_rate: float | None = None
    explicit_mislabel_rate: float | None = None
    cross_document_citation_rate: float | None = None


class RunManifest(BaseModel):
    """Metadata for a single orchestration run."""

    run_id: str = Field(default_factory=lambda: str(uuid4()))
    document_id: str
    seed: int
    decoys_in_prompt: list[str] = Field(default_factory=list)
    condition: str
    strategy: str
    models: dict[str, list[str]] = Field(default_factory=dict)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class RunResult(BaseModel):
    """Full result of an orchestration run."""

    run_id: str
    document_id: str
    document_type: str = "msa"
    condition: str
    strategy: str
    seed: int
    decoys_in_prompt: list[str]
    verified_claims: list[VerifiedClaim]
    task_scores: dict[str, bool]
    metrics: RunMetrics


class TaskResponse(BaseModel):
    """Parsed LLM response for one task invocation."""

    task: str
    model: str
    claims: list[Claim]
