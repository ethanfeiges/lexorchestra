"""Tests for experiment doc sync script."""

from benchmark.experiment import DEFAULT_DOCUMENTS
from scripts.sync_experiment_docs import check_docs, collect_state

LIVE_GOLD_RUNS = len(DEFAULT_DOCUMENTS) * 2


def test_collect_state_matches_expected_run_counts():
    state = collect_state()
    assert state["live_gemini"]["result_count"] == LIVE_GOLD_RUNS or state["live_gemini"]["result_count"] >= 4


def test_check_docs_passes_for_current_catalog():
    state = collect_state()
    errors = check_docs(state)
    assert errors == []
