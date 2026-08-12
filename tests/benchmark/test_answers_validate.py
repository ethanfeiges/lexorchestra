"""Tests for benchmark answer validation."""

from benchmark.answers_validate import assert_all_answers_valid, validate_all_answers


def test_all_fixture_answers_valid():
    assert_all_answers_valid(
        [
            "edgar_edgemode_inc_ex10.1",
            "edgar_nuscale_power_corp_ex10.15",
        ]
    )


def test_validate_returns_empty_for_edgemode():
    report = validate_all_answers(["edgar_edgemode_inc_ex10.1"])
    assert report["edgar_edgemode_inc_ex10.1"] == []
