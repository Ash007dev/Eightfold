from __future__ import annotations

import json
import logging
from typing import Any

from transformer.cache import SQLiteCache, stable_hash
from transformer.config import AppConfig

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.cache = SQLiteCache(config.cache_path)

    def _model_for_tier(self, tier: str) -> str:
        model = self.config.llm_model_cheap if tier == "cheap" and self.config.llm_model_cheap else self.config.llm_model
        return model

    def _call_openai(self, model: str, prompt: str, temperature: float, include_temperature: bool = True) -> str:
        from openai import OpenAI

        client = OpenAI()
        params: dict[str, Any] = {
            "model": model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Return only valid JSON. Do not infer missing values."},
                {"role": "user", "content": prompt},
            ],
        }
        if include_temperature:
            params["temperature"] = temperature
        response = client.chat.completions.create(**params)
        return response.choices[0].message.content or "{}"

    def _call_provider(self, model: str, prompt: str, temperature: float, include_temperature: bool = True) -> str:
        provider = self.config.llm_provider.lower()
        if provider == "openai":
            return self._call_openai(model, prompt, temperature, include_temperature)
        raise ValueError(f"unsupported LLM provider {self.config.llm_provider}; set LLM_PROVIDER=OpenAI")

    @staticmethod
    def _is_temperature_error(exc: Exception) -> bool:
        message = str(exc).lower()
        return "temperature" in message or "unsupported" in message

    def complete(self, prompt: str, tier: str = "strong") -> str:
        temperature = float(self.config.llm_temperature)
        model = self._model_for_tier(tier)
        key = stable_hash(f"{self.config.llm_provider}|{model}|{temperature}|{tier}|{prompt}")
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        if not model:
            value = "{}"
            self.cache.set(key, value)
            return value
        try:
            try:
                value = self._call_provider(model, prompt, temperature, include_temperature=True)
            except Exception as exc:
                if not self._is_temperature_error(exc):
                    raise
                value = self._call_provider(model, prompt, temperature, include_temperature=False)
            json.loads(value)
        except Exception as exc:
            logger.warning("LLM extraction returned nothing (model=%s): %s", model, exc)
            return "{}"
        self.cache.set(key, value)
        return value

    def selftest(self) -> tuple[bool, str]:
        model = self._model_for_tier("strong")
        if not model:
            return False, "LLM_MODEL is empty"
        prompt = 'Return JSON exactly like this: {"ok": true}'
        try:
            try:
                value = self._call_provider(model, prompt, float(self.config.llm_temperature), include_temperature=True)
            except Exception as exc:
                if not self._is_temperature_error(exc):
                    raise
                value = self._call_provider(model, prompt, float(self.config.llm_temperature), include_temperature=False)
            parsed = json.loads(value)
            if not isinstance(parsed, dict):
                return False, f"model={model} returned non-object JSON"
            return True, f"OK model={model}"
        except Exception as exc:
            return False, f"model={model}: {exc}"
