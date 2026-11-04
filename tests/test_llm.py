"""Provider clients, tested offline: HTTP calls are answered by fakes."""

import json

import httpx
import pytest

from dispute_agent.config import load_config
from dispute_agent.llm import LLMError, get_llm
from dispute_agent.llm.ollama import OllamaClient
from dispute_agent.schemas import BaselineJudgement

GOOD = {"eligible": True, "outcome": "decline", "confidence": 0.8, "reasons": ["r"], "citations": ["BPR-02"]}


def _ollama(handler) -> OllamaClient:
    client = OllamaClient(model="test-model:8b", host="http://ollama.test")
    client.http = httpx.Client(transport=httpx.MockTransport(handler))
    return client


def _reply(content: str, **extra) -> httpx.Response:
    return httpx.Response(200, json={"message": {"content": content}, "prompt_eval_count": 100, "eval_count": 20, **extra})


def test_ollama_sends_schema_and_parses_reply():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append(body)
        return _reply(json.dumps(GOOD))

    client = _ollama(handler)
    out = client.generate(task="baseline", system="s", prompt="p", schema=BaselineJudgement)
    assert out.outcome == "decline"
    body = seen[0]
    assert body["format"]["title"] == "BaselineJudgement"
    assert body["options"]["temperature"] == 0.0 and body["options"]["num_ctx"] >= 8192
    assert body["think"] is False and body["stream"] is False
    assert client.stats.calls == 1 and client.stats.tokens_in == 100 and client.stats.tokens_out == 20


def test_ollama_retries_once_on_bad_json_then_fails():
    replies = iter([_reply("not json"), _reply("still not json")])
    client = _ollama(lambda request: next(replies))
    with pytest.raises(LLMError, match="did not match"):
        client.generate(task="baseline", system="s", prompt="p", schema=BaselineJudgement)


def test_ollama_drops_think_flag_for_models_without_thinking():
    bodies = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        bodies.append(body)
        if "think" in body:
            return httpx.Response(400, json={"error": '"test-model:8b" does not support thinking'})
        return _reply(json.dumps(GOOD))

    client = _ollama(handler)
    client.generate(task="baseline", system="s", prompt="p", schema=BaselineJudgement)
    assert "think" in bodies[0] and "think" not in bodies[1]
    assert client.send_think_flag is False


def test_ollama_missing_model_gives_a_clear_error():
    client = _ollama(lambda request: httpx.Response(404, json={"error": "model not found"}))
    with pytest.raises(LLMError, match="ollama pull test-model:8b"):
        client.generate(task="baseline", system="s", prompt="p", schema=BaselineJudgement)


def test_ollama_not_running_gives_a_clear_error():
    def handler(request):
        raise httpx.ConnectError("refused")

    with pytest.raises(LLMError, match="not reachable"):
        _ollama(handler).generate(task="baseline", system="s", prompt="p", schema=BaselineJudgement)


def test_get_llm_picks_provider_and_model():
    llm = get_llm(provider="ollama", model="llama3.1:8b")
    assert llm.name == "ollama" and llm.model == "llama3.1:8b"
    assert get_llm(provider="ollama").model == load_config()["llm"]["judge_models"]["ollama"]
    assert get_llm(provider="mock").name == "mock"
    with pytest.raises(LLMError):
        get_llm(provider="nonsense")


class _Fake:
    """A client that fails with the given errors in turn, then answers."""

    def __init__(self, name, errors=()):
        from dispute_agent.llm import CallStats

        self.name, self.model, self.stats = name, f"{name}-model", CallStats()
        self.errors = list(errors)
        self.calls = 0

    def generate(self, **kw):
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)
        self.stats.record(kw.get("task", ""), 0.1)
        return BaselineJudgement(**GOOD)


def _call(llm):
    return llm.generate(task="baseline", system="s", prompt="p", schema=BaselineJudgement)


def test_fallback_uses_the_primary_when_it_works():
    from dispute_agent.llm import CloudFallbackLLM

    primary, backup = _Fake("gemini"), _Fake("openai")
    llm = CloudFallbackLLM(primary, backup)
    _call(llm)
    assert primary.calls == 1 and backup.calls == 0 and not llm.using_backup and llm.name == "gemini"


def test_daily_quota_switches_to_the_backup_for_the_session():
    from dispute_agent.llm import CloudFallbackLLM, RateLimitError

    primary, backup = _Fake("gemini", [RateLimitError("quota", daily=True)]), _Fake("openai")
    llm = CloudFallbackLLM(primary, backup)
    _call(llm)
    _call(llm)
    assert primary.calls == 1 and backup.calls == 2 and llm.using_backup and llm.model == "openai-model"


def test_other_failures_fall_back_for_one_call_only():
    from dispute_agent.llm import CloudFallbackLLM, LLMError

    primary, backup = _Fake("gemini", [LLMError("503 overloaded")]), _Fake("openai")
    llm = CloudFallbackLLM(primary, backup)
    _call(llm)
    assert llm.using_backup
    _call(llm)
    assert primary.calls == 2 and backup.calls == 1 and not llm.using_backup


def test_fallback_calls_are_capped():
    from dispute_agent.llm import CloudFallbackLLM, RateLimitError

    primary = _Fake("gemini", [RateLimitError("quota", daily=True)])
    llm = CloudFallbackLLM(primary, _Fake("openai"), max_backup_calls=1)
    _call(llm)
    with pytest.raises(RateLimitError, match="limit of 1 calls"):
        _call(llm)


def test_app_gets_the_fallback_only_when_asked_and_keys_are_set(monkeypatch):
    from dispute_agent.llm import CloudFallbackLLM
    from dispute_agent.llm.gemini import GeminiClient

    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert isinstance(get_llm(provider="gemini", with_fallback=True), CloudFallbackLLM)
    assert isinstance(get_llm(provider="gemini"), GeminiClient)  # evaluations never fall back
    monkeypatch.delenv("OPENAI_API_KEY")
    assert isinstance(get_llm(provider="gemini", with_fallback=True), GeminiClient)


def test_openai_without_key_is_a_clear_error(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(LLMError, match="OPENAI_API_KEY"):
        get_llm(provider="openai")


def test_openai_client_parses_structured_output(monkeypatch):
    from types import SimpleNamespace

    from dispute_agent.llm.openai_client import OpenAIClient

    client = OpenAIClient(model="gpt-5-mini", api_key="sk-test")
    calls = []

    def fake_parse(**kwargs):
        calls.append(kwargs)
        message = SimpleNamespace(parsed=BaselineJudgement(**GOOD), refusal=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=SimpleNamespace(prompt_tokens=50, completion_tokens=10))

    monkeypatch.setattr(client.client.chat.completions, "parse", fake_parse)
    out = client.generate(task="baseline", system="s", prompt="p", schema=BaselineJudgement)
    assert out.outcome == "decline"
    assert calls[0]["response_format"] is BaselineJudgement
    assert "temperature" not in calls[0]  # gpt-5 models only take the default
    assert client.stats.tokens_in == 50
