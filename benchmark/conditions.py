"""Experimental conditions and per-run prompt assembly."""

from __future__ import annotations

import random
import secrets
from dataclasses import dataclass

from docProcessing.models import SoTBundle
from docProcessing.prompt import format_candidates_for_prompt

CONDITIONS = ("clean", "noisy_prompt", "noisy_task", "unlabeled_noisy")

UNLABELED_HEADER = "Document versions (labels are arbitrary):"

DECOY_LABELS = [
    "draft_missing_section",
    "outdated_wrong_terms",
    "bad_parse_extra_clause",
    "bad_parse_wrong_ids",
]


def fresh_seed() -> int:
    """Random seed for eval runs (not fixed 42)."""
    return secrets.randbelow(2**31)


def sample_decoys(seed: int, condition: str) -> list[str]:
    """Sample which decoys appear in the prompt for a run."""
    if condition == "clean":
        return []

    rng = random.Random(seed)
    count = rng.randint(1, 2)
    decoys = rng.sample(DECOY_LABELS, k=min(count, len(DECOY_LABELS)))
    return decoys


def unlabeled_aliases(decoys: list[str], seed: int) -> dict[str, str]:
    """Map internal candidate labels to anonymous version_N display labels."""
    internal = ["signed_contract"] + list(decoys)
    rng = random.Random(seed + 2)
    ordered = internal.copy()
    rng.shuffle(ordered)
    return {label: f"version_{index + 1}" for index, label in enumerate(ordered)}


def prompt_labels_for_condition(condition: str, decoys: list[str]) -> list[str]:
    """Build ordered label list for format_candidates_for_prompt."""
    labels = ["signed_contract"] + list(decoys)
    if condition in ("noisy_prompt", "noisy_task", "unlabeled_noisy") and len(decoys) > 1:
        rng = random.Random(hash(tuple(decoys)))
        rest = decoys.copy()
        rng.shuffle(rest)
        labels = ["signed_contract"] + rest
    return labels


@dataclass
class PromptContext:
    """Assembled prompt state for one run."""

    document_block: str
    decoys_in_prompt: list[str]
    prompt_labels: list[str]
    label_aliases: dict[str, str] | None = None
    prompt_header: str | None = None


def build_prompt_context(
    bundle: SoTBundle,
    condition: str,
    seed: int,
) -> PromptContext:
    """Build document prompt block and decoy selection for a run."""
    if condition not in CONDITIONS:
        raise ValueError(f"Unknown condition: {condition}")

    decoys = sample_decoys(seed, condition)
    labels = prompt_labels_for_condition(condition, decoys)

    rng = random.Random(seed + 1)
    if condition != "clean" and len(labels) > 1:
        signed = labels[0]
        rest = labels[1:]
        rng.shuffle(rest)
        labels = [signed] + rest

    label_aliases: dict[str, str] | None = None
    prompt_header: str | None = None
    if condition == "unlabeled_noisy":
        label_aliases = unlabeled_aliases(decoys, seed)
        prompt_header = UNLABELED_HEADER

    block = format_candidates_for_prompt(
        bundle.candidates,
        labels=labels,
        header=prompt_header,
        label_aliases=label_aliases,
    )
    return PromptContext(
        document_block=block,
        decoys_in_prompt=decoys,
        prompt_labels=labels,
        label_aliases=label_aliases,
        prompt_header=prompt_header,
    )
