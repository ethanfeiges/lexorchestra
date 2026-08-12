"""Data models for the SoT layer."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class Clause(BaseModel):
    """A single clause from a parsed document."""

    id: str
    text: str
    start_offset: int
    end_offset: int

    @model_validator(mode="after")
    def validate_offsets(self) -> Clause:
        if self.start_offset < 0 or self.end_offset < self.start_offset:
            raise ValueError(
                f"Invalid offsets for clause {self.id}: "
                f"start={self.start_offset}, end={self.end_offset}"
            )
        return self


class SoTCandidate(BaseModel):
    """One document version in an SoT bundle (canonical or decoy)."""

    label: str
    valid: bool
    clauses: list[Clause]
    corruption: str | None = None


class SoTBundle(BaseModel):
    """Canonical clauses plus labeled candidate versions for experiments."""

    document_id: str
    source_path: str
    canonical: list[Clause]
    candidates: list[SoTCandidate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_bundle(self) -> SoTBundle:
        valid_candidates = [c for c in self.candidates if c.valid]
        if len(valid_candidates) != 1:
            raise ValueError(
                f"Expected exactly one valid candidate, found {len(valid_candidates)}"
            )
        signed = valid_candidates[0]
        if signed.label != "signed_contract":
            raise ValueError(
                f"Valid candidate must have label 'signed_contract', got '{signed.label}'"
            )
        if signed.corruption is not None:
            raise ValueError("Valid candidate must have corruption=None")
        if signed.clauses != self.canonical:
            raise ValueError("signed_contract clauses must match canonical")
        return self
