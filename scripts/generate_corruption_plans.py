"""Pre-generate document-specific corruption plans via Gemini."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from docProcessing.corruption_plan import resolve_corruption_plan
from docProcessing.parser import parse_document

CONTRACTS_DIR = Path(__file__).resolve().parents[1] / "legalDocs" / "contracts" / "public"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate cached corruption plans for contract documents."
    )
    parser.add_argument(
        "--mode",
        choices=("local", "gemini", "auto"),
        default="gemini",
        help="local = regex-based; gemini = LLM; auto = gemini if API key set",
    )
    parser.add_argument("--seed", type=int, default=42, help="Corruption seed")
    parser.add_argument(
        "--document",
        type=str,
        default="",
        help="Single document stem (default: all public contracts)",
    )
    args = parser.parse_args()

    paths = (
        [CONTRACTS_DIR / f"{args.document}.txt"]
        if args.document
        else sorted(CONTRACTS_DIR.glob("*.txt"))
    )

    for path in paths:
        if not path.exists():
            print(f"skip missing {path.name}")
            continue
        clauses = parse_document(path)
        plan = resolve_corruption_plan(
            clauses,
            path.stem,
            args.seed,
            mode=args.mode,
            use_cache=True,
        )
        print(
            json.dumps(
                {
                    "document_id": plan.document_id,
                    "mode": plan.mode,
                    "edits": len(plan.span_edits),
                    "categories": sorted({e.category for e in plan.span_edits}),
                }
            )
        )


if __name__ == "__main__":
    main()
