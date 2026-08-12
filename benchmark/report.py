"""Generate markdown reports from experiment result JSON."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_results(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def summarize_by_key(
    results: list[dict[str, Any]], key: str
) -> dict[str, dict[str, float]]:
    """Aggregate mean metrics grouped by a result field."""
    buckets: dict[str, list[dict[str, float]]] = defaultdict(list)
    for row in results:
        buckets[row[key]].append(row["metrics"])
    out: dict[str, dict[str, float]] = {}
    for group, metrics_list in sorted(buckets.items()):
        n = len(metrics_list)
        out[group] = {
            "grounding_rate": sum(m["grounding_rate"] for m in metrics_list) / n,
            "decoy_citation_rate": sum(m["decoy_citation_rate"] for m in metrics_list) / n,
            "task_accuracy": sum(m["task_accuracy"] for m in metrics_list) / n,
            "runs": n,
        }
    return out


def render_markdown(
    results: list[dict[str, Any]],
    *,
    title: str = "LexOrchestra Experiment Report",
    meta: dict[str, Any] | None = None,
) -> str:
    """Render a GitHub-friendly markdown report."""
    meta = meta or {}
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# {title}",
        "",
        f"Generated: {generated}",
        "",
    ]
    if meta:
        lines.append("## Run configuration")
        lines.append("")
        for k, v in meta.items():
            lines.append(f"- **{k}**: `{v}`")
        lines.append("")

    lines.extend(
        [
            "## Summary by condition",
            "",
            "| Condition | Runs | Grounding | Decoy rate | Task accuracy |",
            "|-----------|------|-----------|------------|---------------|",
        ]
    )
    for cond, stats in summarize_by_key(results, "condition").items():
        lines.append(
            f"| {cond} | {int(stats['runs'])} | {stats['grounding_rate']:.0%} | "
            f"{stats['decoy_citation_rate']:.0%} | {stats['task_accuracy']:.0%} |"
        )

    if any("model" in r for r in results):
        lines.extend(
            [
                "",
                "## Summary by model",
                "",
                "| Model | Runs | Grounding | Decoy rate | Task accuracy |",
                "|-------|------|-----------|------------|---------------|",
            ]
        )
        for model, stats in summarize_by_key(results, "model").items():
            lines.append(
                f"| {model} | {int(stats['runs'])} | {stats['grounding_rate']:.0%} | "
                f"{stats['decoy_citation_rate']:.0%} | {stats['task_accuracy']:.0%} |"
            )

    if any("document_type" in r for r in results):
        lines.extend(
            [
                "",
                "## Summary by document type",
                "",
                "| Document type | Runs | Grounding | Decoy rate | Task accuracy |",
                "|---------------|------|-----------|------------|---------------|",
            ]
        )
        for dtype, stats in summarize_by_key(results, "document_type").items():
            lines.append(
                f"| {dtype} | {int(stats['runs'])} | {stats['grounding_rate']:.0%} | "
                f"{stats['decoy_citation_rate']:.0%} | {stats['task_accuracy']:.0%} |"
            )

    lines.extend(
        [
            "",
            "## Summary by strategy",
            "",
            "| Strategy | Runs | Grounding | Decoy rate | Task accuracy |",
            "|----------|------|-----------|------------|---------------|",
        ]
    )
    for strategy, stats in summarize_by_key(results, "strategy").items():
        lines.append(
            f"| {strategy} | {int(stats['runs'])} | {stats['grounding_rate']:.0%} | "
            f"{stats['decoy_citation_rate']:.0%} | {stats['task_accuracy']:.0%} |"
        )

    lines.extend(["", "## Per-run detail", ""])
    lines.append(
        "| Document | Type | Condition | Strategy | Model | Seed | Decoys | Ground | Decoy | Acc |"
    )
    lines.append(
        "|----------|------|-----------|----------|-------|------|--------|--------|-------|-----|"
    )
    for row in results:
        m = row["metrics"]
        decoys = ", ".join(row.get("decoys_in_prompt") or []) or "—"
        model = row.get("model", "—")
        dtype = row.get("document_type", "—")
        lines.append(
            f"| {row['document_id']} | {dtype} | {row['condition']} | {row['strategy']} | "
            f"{model} | {row['seed']} | {decoys} | {m['grounding_rate']:.0%} | "
            f"{m['decoy_citation_rate']:.0%} | {m['task_accuracy']:.0%} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- **Grounding rate** measures whether claims cite valid clause IDs and exact quotes "
            "from the canonical signed contract.",
            "- **Decoy citation rate** rises when the model anchors on corrupted document versions "
            "shown in the prompt.",
            "- **Task accuracy** compares verified answers against pre-authored gold labels.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(
    results_path: Path,
    report_path: Path,
    *,
    title: str = "LexOrchestra Experiment Report",
    meta: dict[str, Any] | None = None,
) -> str:
    results = load_results(results_path)
    md = render_markdown(results, title=title, meta=meta)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(md, encoding="utf-8")
    return md
