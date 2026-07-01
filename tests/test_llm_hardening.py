"""LLM failures must be visible and transient errors must not poison the cache."""

from pathlib import Path

from transformer.config import AppConfig
from transformer.llm import LLMClient


def test_temperature_error_retries_without_temperature(tmp_path, monkeypatch) -> None:
    calls: list[bool] = []
    client = LLMClient(AppConfig(llm_model="model", cache_path=str(tmp_path / "cache.db")))

    def fake_call_provider(model: str, prompt: str, temperature: float, include_temperature: bool = True) -> str:
        del model, prompt, temperature
        calls.append(include_temperature)
        if include_temperature:
            raise ValueError("unsupported temperature")
        return '{"ok": true}'

    monkeypatch.setattr(client, "_call_provider", fake_call_provider)
    assert client.complete("prompt") == '{"ok": true}'
    assert calls == [True, False]


def test_final_llm_failure_is_not_cached(tmp_path, monkeypatch) -> None:
    calls = {"count": 0}
    cache_path = str(tmp_path / "cache.db")
    client = LLMClient(AppConfig(llm_model="model", cache_path=cache_path))

    def fake_call_provider(model: str, prompt: str, temperature: float, include_temperature: bool = True) -> str:
        del model, prompt, temperature, include_temperature
        calls["count"] += 1
        raise RuntimeError("network down")

    monkeypatch.setattr(client, "_call_provider", fake_call_provider)
    assert client.complete("prompt") == "{}"
    assert client.complete("prompt") == "{}"
    assert calls["count"] == 2
