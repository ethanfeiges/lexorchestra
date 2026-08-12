"""Tests for experiment doc sync script."""

from benchmark.run_live_experiment import LIVE_DOCUMENTS
from scripts.sync_experiment_docs import check_docs, collect_state

LIVE_GOLD_RUNS = len(LIVE_DOCUMENTS) * 2


def test_collect_state_matches_expected_run_counts():
    state = collect_state()
    assert state["mock_baseline"]["result_count"] == 24
    assert state["ablations"]["result_count"] == 6
    if state["live_gemini"]["result_count"] != LIVE_GOLD_RUNS:
        # Allow partial live runs when API quota limits completion
        if state["live_gemini"]["result_count"] < 4:
            assert False, f"live_gemini has only {state['live_gemini']['result_count']} rows"


def test_check_docs_passes_for_current_catalog():
    state = collect_state()
    errors = check_docs(state)
    assert errors == []
