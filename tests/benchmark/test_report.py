"""Tests for experiment report generation."""

from benchmark.report import render_markdown


def test_render_markdown_includes_profiles():
    results = [
        {
            "document_id": "doc",
            "condition": "noisy_prompt",
            "strategy": "single",
            "mock_profile": "decoy_anchored",
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
    assert "decoy_anchored" in md
    assert "noisy_prompt" in md


def test_render_markdown_includes_ablation_summary():
    results = [
        {
            "document_id": "doc",
            "condition": "noisy_prompt",
            "strategy": "single",
            "mock_profile": "decoy_anchored",
            "ablation": "no_verifier",
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
    assert "Summary by ablation" in md
    assert "no_verifier" in md
    assert "Ablation" in md
