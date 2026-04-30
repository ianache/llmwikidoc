"""Gemini client wrapper — generate and embed with retry."""

from __future__ import annotations

import json
import time
from typing import Any

from google import genai
from google.genai import types

from llmwikidoc.config import Config


class LLMClient:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._client = genai.Client(api_key=config.api_key)

    def generate(self, prompt: str, *, json_output: bool = False) -> str:
        """Send a prompt to Gemini and return the text response."""
        generate_config = None
        if json_output:
            generate_config = types.GenerateContentConfig(
                response_mime_type="application/json"
            )

        for attempt in range(3):
            try:
                response = self._client.models.generate_content(
                    model=self._config.model,
                    contents=prompt,
                    config=generate_config,
                )
                return response.text or ""
            except Exception as exc:
                if attempt == 2:
                    raise
                # Exponential backoff: 2s, 4s
                time.sleep(2 ** (attempt + 1))
                continue
        return ""  # unreachable

    def generate_structured(self, prompt: str) -> dict[str, Any]:
        """Generate a JSON response and parse it into a dict."""
        raw = self.generate(prompt, json_output=True)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Gemini returned invalid JSON: {raw[:200]}") from exc

    def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for text."""
        response = self._client.models.embed_content(
            model="gemini-embedding-001",
            contents=text,
        )
        return response.embeddings[0].values

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> LLMClient:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
