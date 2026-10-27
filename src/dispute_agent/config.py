"""Settings from config.yaml plus secrets from .env."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_JUDGE_MODEL = "gemini-flash-lite-latest"


@lru_cache(maxsize=1)
def load_config() -> dict[str, Any]:
    load_dotenv(ROOT / ".env")
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    env_model = os.getenv("GEMINI_MODEL", "").strip()
    if env_model:
        cfg["llm"]["judge_model"] = env_model
    cfg["llm"]["judge_model"] = cfg["llm"].get("judge_model") or DEFAULT_JUDGE_MODEL
    env_provider = os.getenv("LLM_PROVIDER", "").strip()
    if env_provider:
        cfg["llm"]["provider"] = env_provider
    return cfg


def path(key: str) -> Path:
    """Resolve a dotted config key such as 'data.seed_cases' to an absolute path."""
    node: Any = load_config()
    for part in key.split("."):
        node = node[part]
    return ROOT / node


def gemini_api_key() -> str | None:
    load_config()
    key = os.getenv("GEMINI_API_KEY", "").strip()
    return key or None
