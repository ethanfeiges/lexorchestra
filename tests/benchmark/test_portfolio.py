"""Portfolio assembly and prompt formatting tests."""

from benchmark.portfolio import (
    PORTFOLIO_HEADER,
    build_portfolio_context,
    format_portfolio_for_prompt,
)

TWO_DOC_IDS = [
    "edgar_edgemode_inc_ex10.1",
    "edgar_amd_ex10.79",
]


def test_format_portfolio_for_prompt_labels_each_document():
    ctx = build_portfolio_context(
        document_ids=TWO_DOC_IDS,
        condition="portfolio_clean",
        seed=42,
    )
    block = format_portfolio_for_prompt(list(ctx.documents))
    assert block.startswith(PORTFOLIO_HEADER)
    for doc_id in TWO_DOC_IDS:
        assert f"[signed_contract:{doc_id}]" in block


def test_cross_type_mislabeled_swaps_content_under_label():
    clean = build_portfolio_context(
        document_ids=TWO_DOC_IDS,
        condition="portfolio_clean",
        seed=42,
    )
    mislabeled = build_portfolio_context(
        document_ids=TWO_DOC_IDS,
        condition="cross_type_mislabeled",
        seed=42,
    )
    assert len(mislabeled.mislabeled) == 1
    label_doc, source_doc = mislabeled.mislabeled[0]
    clean_label = next(d for d in clean.documents if d.document_id == label_doc)
    source = next(d for d in mislabeled.documents if d.document_id == source_doc)
    mis_block = mislabeled.document_block
    sample = source.bundle.canonical[0]
    assert f"[signed_contract:{label_doc}] {sample.id}:" in mis_block
    assert sample.text[:40].replace("\n", " ") in mis_block
