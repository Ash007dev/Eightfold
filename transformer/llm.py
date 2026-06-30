from __future__ import annotations

import json
import logging

from transformer.cache import SQLiteCache, stable_hash
from transformer.config import AppConfig

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.cache = SQLiteCache(config.cache_path)

    def complete(self, prompt: str, tier: str = "strong") -> str:
        temperature = 0.0
        model = self.config.llm_model_cheap if tier == "cheap" and self.config.llm_model_cheap else self.config.llm_model
        key = stable_hash(f"{self.config.llm_provider}|{model}|{temperature}|{tier}|{prompt}")
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        if not model:
            value = "{}"
            self.cache.set(key, value)
            return value
        try:
            if self.config.llm_provider.lower() != "openai":
                raise ValueError(f"unsupported LLM provider {self.config.llm_provider}")
            from openai import OpenAI

            client = OpenAI()
            response = client.chat.completions.create(
                model=model,
                temperature=temperature,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "Return only valid JSON. Do not infer missing values."},
                    {"role": "user", "content": prompt},
                ],
            )
            value = response.choices[0].message.content or "{}"
            json.loads(value)
        except Exception as exc:
            logger.warning("llm completion failed: %s", exc)
            value = "{}"
        self.cache.set(key, value)
        return value
