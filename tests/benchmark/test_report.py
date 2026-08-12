"""Tests for experiment report generation."""

from benchmark.report import render_markdown


def test_render_markdown_includes_model_summary():
    results = [
        {
            "document_id": "doc",
            "condition": "noisy_prompt",
            "strategy": "parallel_grounded",
            "model": "gemini-flash-latest",
            "seed": 1,
            "decoys_in_prompt": ["outdated_wrong_terms"],
            "metrics": {
                "grounding_rate": 0.5,
                "decoy_citation_rate": 0.5,
                "task_accuracy": 0.5,
            },
        }
    ]
    md = render_markdown(results)
    assert "gemini-flash-latest" in md
    assert "noisy_prompt" in md
    assert "Summary by model" in md


def test_render_markdown_includes_strategy_summary():
    results = [
        {
            "document_id": "doc",
            "condition": "clean",
            "strategy": "single",
            "model": "gemini-flash-latest",
            "seed": 1,
            "decoys_in_prompt": [],
            "metrics": {
                "grounding_rate": 1.0,
                "decoy_citation_rate": 0.0,
                "task_accuracy": 1.0,
            },
        }
    ]
    md = render_markdown(results)
    assert "Summary by strategy" in md
    assert "single" in md
