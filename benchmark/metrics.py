"""Run metrics and task scoring."""

from __future__ import annotations

import re

from benchmark.answers import DocumentAnswers, ExtractQuestionAnswer, PlaybookRuleAnswer
from orchestrator.models import RunMetrics, VerifiedClaim


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).lower()


def score_playbook_claim(
    verified: VerifiedClaim,
    rule: PlaybookRuleAnswer,
) -> bool:
    """Score one playbook claim against the answer key."""
    if verified.status != "grounded":
        return False
    claim = verified.claim
    if claim.rule_id is not None and claim.rule_id != rule.id:
        return False
    if claim.verdict != rule.expected:
        return False
    if rule.canonical_clause_ids and claim.clause_id not in rule.canonical_clause_ids:
        return False
    for needle in rule.required_substrings:
        if needle.lower() not in _normalize(claim.quote):
            return False
    return True


def score_extract_claim(
    verified: VerifiedClaim,
    question: ExtractQuestionAnswer,
) -> bool:
    """Score one extract claim against the answer key."""
    if verified.status != "grounded":
        return False
    claim = verified.claim
    if claim.clause_id not in question.acceptable_clause_ids:
        return False
    for needle in question.required_substrings:
        if needle.lower() not in _normalize(claim.quote):
            return False
    return True


def build_task_scores(
    verified: list[VerifiedClaim],
    answers: DocumentAnswers,
    *,
    naive: bool = False,
) -> dict[str, bool]:
    """Score each benchmark task using best matching verified claim per model."""
    scores: dict[str, bool] = {}
    playbook_scorer = score_playbook_claim_naive if naive else score_playbook_claim
    extract_scorer = score_extract_claim_naive if naive else score_extract_claim

    canonical_verified = [v for v in verified if v.task in ("extract", "playbook")]

    for rule in answers.rules:
        key = f"playbook:{rule.id}"
        rule_claims = [
            v for v in canonical_verified if v.task == "playbook" and v.claim.rule_id == rule.id
        ]
        if not rule_claims:
            rule_claims = [v for v in canonical_verified if v.task == "playbook"]
        scores[key] = any(playbook_scorer(v, rule) for v in rule_claims)

    for question in answers.extract_questions:
        key = f"extract:{question.id}"
        extract_claims = [v for v in canonical_verified if v.task == "extract"]
        scores[key] = any(extract_scorer(v, question) for v in extract_claims)

    return scores


def build_portfolio_task_scores(
    verified: list[VerifiedClaim],
    answers_by_doc: dict[str, DocumentAnswers],
    *,
    naive: bool = False,
) -> dict[str, bool]:
    """Score portfolio tasks keyed as document_id:playbook:rule_id."""
    scores: dict[str, bool] = {}
    for doc_id, answers in answers_by_doc.items():
        doc_verified = []
        for v in verified:
            if v.expected_document_id != doc_id and v.claim.document_id != doc_id:
                continue
            if v.task == f"playbook:{doc_id}":
                doc_verified.append(v.model_copy(update={"task": "playbook"}))
            elif v.task == f"extract:{doc_id}":
                doc_verified.append(v.model_copy(update={"task": "extract"}))
        doc_scores = build_task_scores(doc_verified, answers, naive=naive)
        for key, ok in doc_scores.items():
            scores[f"{doc_id}:{key}"] = ok
    return scores


def compute_portfolio_metrics(
    verified: list[VerifiedClaim],
    task_scores: dict[str, bool],
    *,
    trust_model_labels: bool = False,
) -> RunMetrics:
    """Aggregate metrics for a portfolio run."""
    metrics = compute_metrics(verified, task_scores, trust_model_labels=trust_model_labels)

    canonical = [
        v
        for v in verified
        if v.task.startswith("extract:") or v.task.startswith("playbook:")
    ]
    discriminate = [v for v in verified if v.task.startswith("extract_discriminate:")]

    cross_doc = sum(1 for v in verified if v.cross_document_match is not None)
    cross_document_citation_rate = cross_doc / len(verified) if verified else 0.0

    source_fidelity: float | None = None
    if canonical:
        canon_grounded = sum(1 for v in canonical if v.status == "grounded")
        source_fidelity = canon_grounded / len(canonical)

    explicit_mislabel_rate: float | None = None
    if discriminate:
        mislabeled = sum(
            1
            for v in discriminate
            if v.claim.document_id
            and v.expected_document_id
            and v.claim.document_id != v.expected_document_id
        )
        explicit_mislabel_rate = mislabeled / len(discriminate)

    return metrics.model_copy(
        update={
            "source_fidelity": source_fidelity,
            "cross_document_citation_rate": cross_document_citation_rate,
            "explicit_mislabel_rate": explicit_mislabel_rate,
        }
    )


def score_playbook_claim_naive(
    verified: VerifiedClaim,
    rule: PlaybookRuleAnswer,
) -> bool:
    """Naive playbook score: trust model verdict without quote grounding."""
    claim = verified.claim
    if claim.rule_id is not None and claim.rule_id != rule.id:
        return False
    return claim.verdict == rule.expected


def score_extract_claim_naive(
    verified: VerifiedClaim,
    question: ExtractQuestionAnswer,
) -> bool:
    """Naive extract score: trust clause_id without substring checks."""
    return verified.claim.clause_id in question.acceptable_clause_ids


def compute_metrics(
    verified: list[VerifiedClaim],
    task_scores: dict[str, bool],
    *,
    trust_model_labels: bool = False,
) -> RunMetrics:
    """Aggregate run-level metrics."""
    total = len(verified)
    grounded = sum(1 for v in verified if v.status == "grounded")
    decoy = sum(
        1
        for v in verified
        if v.decoy_match is not None
        or (
            not trust_model_labels
            and v.claim.sot_label is not None
            and v.claim.sot_label != "signed_contract"
        )
    )
    correct = sum(1 for ok in task_scores.values() if ok)
    total_tasks = len(task_scores)

    canonical = [v for v in verified if v.task in ("extract", "playbook")]
    probe = [v for v in verified if v.task == "extract_decoy"]
    discriminate = [v for v in verified if v.task == "extract_discriminate"]

    source_fidelity: float | None = None
    decoy_probe_match_rate: float | None = None
    explicit_mislabel_rate: float | None = None

    if canonical:
        canon_grounded = sum(1 for v in canonical if v.status == "grounded")
        source_fidelity = canon_grounded / len(canonical)

    if probe:
        probe_decoy = sum(1 for v in probe if v.decoy_match is not None)
        decoy_probe_match_rate = probe_decoy / len(probe)

    if discriminate:
        mislabeled = sum(
            1
            for v in discriminate
            if v.claim.sot_label is not None and v.claim.sot_label != "signed_contract"
        )
        explicit_mislabel_rate = mislabeled / len(discriminate)

    return RunMetrics(
        grounding_rate=grounded / total if total else 0.0,
        decoy_citation_rate=decoy / total if total else 0.0,
        task_accuracy=correct / total_tasks if total_tasks else 0.0,
        total_claims=total,
        grounded_claims=grounded,
        decoy_citations=decoy,
        correct_tasks=correct,
        total_tasks=total_tasks,
        source_fidelity=source_fidelity,
        decoy_probe_match_rate=decoy_probe_match_rate,
        explicit_mislabel_rate=explicit_mislabel_rate,
    )
