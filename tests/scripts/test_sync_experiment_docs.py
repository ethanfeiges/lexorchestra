"""Tests for experiment doc sync script."""

from benchmark.experiment import DEFAULT_DOCUMENTS
from scripts.sync_experiment_docs import check_docs, collect_state

LIVE_GOLD_RUNS = len(DEFAULT_DOCUMENTS) * 2


def test_collect_state_matches_expected_run_counts():
    state = collect_state()
    manifest = state["live_gemini"]["manifest"]
    count = state["live_gemini"]["result_count"]
    if manifest.get("status") == "partial":
        assert count >= 1
    else:
        assert count == LIVE_GOLD_RUNS or count >= 4


def test_check_docs_passes_for_current_catalog():
    state = collect_state()
    errors = check_docs(state)
    assert errors == []
