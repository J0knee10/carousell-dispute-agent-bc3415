"""Settings from config.yaml plus secrets from .env (or Streamlit secrets)."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
PROVIDERS = ("gemini", "ollama", "openai", "mock")
DEFAULT_JUDGE_MODELS = {"gemini": "gemini-flash-lite-latest", "ollama": "llama3.1:8b", "openai": "gpt-5-mini"}
# Environment variables that override the judge model for each provider.
MODEL_ENV = {"gemini": "GEMINI_MODEL", "ollama": "OLLAMA_MODEL", "openai": "OPENAI_MODEL"}


@lru_cache(maxsize=1)
def load_config() -> dict[str, Any]:
    load_dotenv(ROOT / ".env")
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    llm = cfg["llm"]
    models = {**DEFAULT_JUDGE_MODELS, **(llm.get("judge_models") or {})}
    for provider, var in MODEL_ENV.items():
        value = os.getenv(var, "").strip()
        if value:
            models[provider] = value
    llm["judge_models"] = models
    env_provider = os.getenv("LLM_PROVIDER", "").strip()
    if env_provider:
        llm["provider"] = env_provider
    env_host = os.getenv("OLLAMA_HOST", "").strip()
    llm.setdefault("ollama", {})
    if env_host:
        llm["ollama"]["host"] = env_host if env_host.startswith("http") else f"http://{env_host}"
    return cfg


def judge_model(provider: str) -> str:
    return load_config()["llm"]["judge_models"].get(provider, "")


def path(key: str) -> Path:
    """Resolve a dotted config key such as 'data.seed_cases' to an absolute path."""
    node: Any = load_config()
    for part in key.split("."):
        node = node[part]
    return ROOT / node


def _secret(name: str) -> str | None:
    load_config()
    key = os.getenv(name, "").strip()
    return key or None


def gemini_api_key() -> str | None:
    return _secret("GEMINI_API_KEY")


def openai_api_key() -> str | None:
    return _secret("OPENAI_API_KEY")
