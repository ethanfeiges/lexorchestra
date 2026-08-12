"""Provider configuration for live LLM benchmark runs."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from models.base import ModelClient
from models.gemini_client import (
    DEFAULT_GEMINI_MODEL,
    build_gemini_client_factory,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class LiveProvider:
    """One live LLM backend for benchmark runs."""

    name: str
    default_model: str
    experiments_dir: str
    mode: str
    env_keys: tuple[str, ...]
    factory_builder: Callable[[str], Callable[[str], ModelClient]]

    def resolve_api_key(self) -> str:
        for key in self.env_keys:
            value = os.environ.get(key, "").strip()
            if value:
                return value
        return ""

    def require_api_key(self) -> None:
        if self.resolve_api_key():
            return
        keys = " or ".join(self.env_keys)
        print(
            f"{keys} is not set.\n"
            "Export it or add it to .env at the repo root, then re-run:\n"
            f"  python -m benchmark.run_live_experiment --provider {self.name}",
            file=sys.stderr,
        )
        raise SystemExit(2)

    def build_factory(self, model: str) -> Callable[[str], ModelClient]:
        return self.factory_builder(model or self.default_model)

    def output_dir(self) -> Path:
        return REPO_ROOT / "experiments" / self.experiments_dir


PROVIDERS: dict[str, LiveProvider] = {
    "gemini": LiveProvider(
        name="gemini",
        default_model=DEFAULT_GEMINI_MODEL,
        experiments_dir="live_gemini",
        mode="live_gemini",
        env_keys=("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        factory_builder=build_gemini_client_factory,
    ),
}


def get_provider(name: str) -> LiveProvider:
    if name not in PROVIDERS:
        known = ", ".join(sorted(PROVIDERS))
        raise ValueError(f"Unknown provider {name!r}; choose from: {known}")
    return PROVIDERS[name]
