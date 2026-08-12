"""Tests for benchmark answer loading."""

from benchmark.answers import list_answer_documents, load_answers


def test_list_answer_documents():
    docs = list_answer_documents()
    assert "edgar_edgemode_inc_ex10.1" in docs
    assert len(docs) >= 3


def test_load_nuscale_answers():
    answers = load_answers("edgar_nuscale_power_corp_ex10.15")
    assert answers.document_id == "edgar_nuscale_power_corp_ex10.15"
    assert len(answers.rules) >= 2
    assert len(answers.extract_questions) >= 1
