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

    if any("mock_profile" in r for r in results):
        lines.extend(
            [
                "",
                "## Summary by mock profile",
                "",
                "| Profile | Runs | Grounding | Decoy rate | Task accuracy |",
                "|---------|------|-----------|------------|---------------|",
            ]
        )
        for profile, stats in summarize_by_key(results, "mock_profile").items():
            lines.append(
                f"| {profile} | {int(stats['runs'])} | {stats['grounding_rate']:.0%} | "
                f"{stats['decoy_citation_rate']:.0%} | {stats['task_accuracy']:.0%} |"
            )

    if any("ablation" in r for r in results):
        lines.extend(
            [
                "",
                "## Summary by ablation",
                "",
                "| Ablation | Runs | Grounding | Decoy rate | Task accuracy |",
                "|----------|------|-----------|------------|---------------|",
            ]
        )
        for ablation, stats in summarize_by_key(results, "ablation").items():
            lines.append(
                f"| {ablation} | {int(stats['runs'])} | {stats['grounding_rate']:.0%} | "
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
    has_ablation = any("ablation" in r for r in results)
    detail_header = (
        "| Document | Condition | Strategy | Profile | Seed | Decoys | Ground | Decoy | Acc | Ablation |"
        if has_ablation
        else "| Document | Condition | Strategy | Profile | Seed | Decoys | Ground | Decoy | Acc |"
    )
    detail_rule = (
        "|----------|-----------|----------|---------|------|--------|--------|-------|-----|----------|"
        if has_ablation
        else "|----------|-----------|----------|---------|------|--------|--------|-------|-----|"
    )
    lines.append(detail_header)
    lines.append(detail_rule)
    for row in results:
        m = row["metrics"]
        decoys = ", ".join(row.get("decoys_in_prompt") or []) or "—"
        profile = row.get("mock_profile", "—")
        row_line = (
            f"| {row['document_id']} | {row['condition']} | {row['strategy']} | "
            f"{profile} | {row['seed']} | {decoys} | {m['grounding_rate']:.0%} | "
            f"{m['decoy_citation_rate']:.0%} | {m['task_accuracy']:.0%} |"
        )
        if has_ablation:
            row_line = f"{row_line} {row.get('ablation', '—')} |"
        lines.append(row_line)

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- **canonical** mock profile simulates agents that always cite `signed_contract` correctly.",
            "- **decoy_anchored** mock profile simulates agents that faithfully use decoy text — "
            "grounding and task accuracy should drop under `noisy_prompt`.",
            "- Comparing profiles on the same seeds shows what the verifier catches without live LLM cost.",
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
