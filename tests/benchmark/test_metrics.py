"""Tests for benchmark metrics."""

from benchmark.answers import load_answers
from benchmark.metrics import build_task_scores, compute_metrics, score_playbook_claim
from orchestrator.models import Claim, VerifiedClaim


def test_score_playbook_grounded_pass():
    answers = load_answers("edgar_nuscale_power_corp_ex10.15")
    rule = next(r for r in answers.rules if r.id == "liability_cap_10m")
    verified = VerifiedClaim(
        claim=Claim(
            statement="Cap present",
            clause_id="c-007",
            quote="shall not exceed the value of the Services then being provided by Fluor under TOs in process but in no event shall be in excess of $10,000,000",
            rule_id="liability_cap_10m",
            verdict="pass",
        ),
        status="grounded",
        model="test",
        task="playbook",
    )
    assert score_playbook_claim(verified, rule) is True


def test_score_playbook_decoy_verdict_fails():
    answers = load_answers("edgar_nuscale_power_corp_ex10.15")
    rule = next(r for r in answers.rules if r.id == "liability_cap_10m")
    verified = VerifiedClaim(
        claim=Claim(
            statement="Wrong cap",
            clause_id="c-007",
            quote="$5,000,000",
            rule_id="liability_cap_10m",
            verdict="pass",
        ),
        status="ungrounded",
        reason="text_mismatch",
        model="test",
        task="playbook",
        decoy_match="outdated_wrong_terms",
    )
    assert score_playbook_claim(verified, rule) is False


def test_compute_metrics():
    verified = [
        VerifiedClaim(
            claim=Claim(statement="a", clause_id="c-001", quote="x"),
            status="grounded",
            model="m",
            task="extract",
        ),
        VerifiedClaim(
            claim=Claim(
                statement="b",
                clause_id="c-002",
                quote="y",
                sot_label="outdated_wrong_terms",
            ),
            status="ungrounded",
            model="m",
            task="playbook",
            decoy_match="outdated_wrong_terms",
        ),
    ]
    scores = {"extract:q1": True, "playbook:r1": False}
    metrics = compute_metrics(verified, scores)
    assert metrics.total_claims == 2
    assert metrics.grounded_claims == 1
    assert metrics.grounding_rate == 0.5
    assert metrics.decoy_citations == 1
    assert metrics.task_accuracy == 0.5
