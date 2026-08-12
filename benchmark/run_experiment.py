"""Run LexOrchestra Gemini experiment (requires GEMINI_API_KEY)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from benchmark.experiment import (
    DEFAULT_CONDITIONS,
    DEFAULT_DOCUMENTS,
    DEFAULT_STRATEGY,
    DEFAULT_STRATEGIES,
    run_gemini_matrix,
    save_results,
)
from benchmark.answers_validate import assert_all_answers_valid
from benchmark.live_providers import PROVIDERS, REPO_ROOT, get_provider
from benchmark.report import write_report

EXPERIMENTS_DIR = REPO_ROOT / "experiments"


def load_dotenv_if_present() -> None:
    """Load .env into os.environ without overriding existing variables."""
    env_path = REPO_ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run LexOrchestra Gemini experiment",
    )
    parser.add_argument(
        "--provider",
        choices=sorted(PROVIDERS),
        default="gemini",
        help="LLM provider (default: gemini)",
    )
    parser.add_argument(
        "--documents",
        nargs="*",
        default=DEFAULT_DOCUMENTS,
        help="Document IDs (default: one primary fixture per document type)",
    )
    parser.add_argument(
        "--conditions",
        nargs="*",
        default=DEFAULT_CONDITIONS,
        help="Prompt conditions (default: clean noisy_prompt)",
    )
    parser.add_argument(
        "--strategies",
        nargs="*",
        default=[DEFAULT_STRATEGY],
        choices=DEFAULT_STRATEGIES,
        help="Orchestration strategy (default: parallel_grounded)",
    )
    parser.add_argument(
        "--include-chime",
        action="store_true",
        help="Include Chime MSA (184 clauses; may hit Gemini token quotas)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Gemini model id (default: gemini-flash-latest)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="JSON output (default: experiments/live_gemini/results.json)",
    )
    parser.add_argument(
        "--skip-answers-check",
        action="store_true",
        help="Skip answer-key validation before run",
    )
    args = parser.parse_args(argv)

    load_dotenv_if_present()
    provider = get_provider(args.provider)
    provider.require_api_key()

    documents = list(args.documents)
    if args.include_chime and "edgar_chime_financial_inc_ex10.1" not in documents:
        documents.append("edgar_chime_financial_inc_ex10.1")
    documents = sorted(set(documents))

    resolved_model = args.model or provider.default_model
    output_path = args.output or (provider.output_dir() / "results.json")
    report_path = output_path.with_name("REPORT.md")
    manifest_path = output_path.with_name("manifest.json")

    run_count = len(documents) * len(args.conditions) * len(args.strategies)
    print(f"LexOrchestra Gemini experiment")
    print(f"  documents: {', '.join(documents)}")
    print(f"  conditions: {', '.join(args.conditions)}")
    print(f"  strategies: {', '.join(args.strategies)}")
    print(f"  provider: {provider.name}")
    print(f"  model: {resolved_model}")
    print(f"  run count: {run_count}")
    print(f"  output: {output_path}")
    print()

    if not args.skip_answers_check:
        print("Validating benchmark answers against canonical parses...")
        assert_all_answers_valid(documents)
        print("  answers OK")
        print()

    results = run_gemini_matrix(
        provider=provider,
        documents=documents,
        conditions=args.conditions,
        strategies=args.strategies,
        model=resolved_model,
        output_path=output_path,
    )

    save_results(results, output_path)

    meta = {
        "mode": provider.mode,
        "status": "completed" if len(results) >= run_count else "partial",
        "provider": provider.name,
        "documents": documents,
        "conditions": args.conditions,
        "strategies": args.strategies,
        "model": resolved_model,
        "deterministic": True,
        "seeds": "DETERMINISTIC_SEEDS",
        "generated": datetime.now(timezone.utc).isoformat(),
        "completed_runs": len(results),
        "expected_runs": run_count,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    write_report(
        output_path,
        report_path,
        title="LexOrchestra Gemini Experiment Report",
        meta=meta,
    )

    print(f"\nResults: {output_path}")
    print(f"Report:  {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
