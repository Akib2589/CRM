# app/ai/provider.py
import json
import logging
from typing import Optional, Dict, Any, Type, List
import httpx
from pydantic import BaseModel
from app.core.config import settings

logger = logging.getLogger(__name__)

FALLBACK_MODELS = [
    "nvidia/nemotron-3.5-lightning:free",
    "liquid/lfm-2.5-2.6b:free",
    "google/gemma-4-31b-it:free",
]

class AIProvider:
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        response_schema: Optional[Type[BaseModel]] = None
    ) -> str:
        raise NotImplementedError

class OpenAICompatibleProvider(AIProvider):
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 30
    ):
        self.api_key = api_key or settings.AI_API_KEY
        self.base_url = (base_url or settings.AI_BASE_URL).rstrip("/")
        self.model = model or settings.AI_MODEL
        self.timeout = timeout or settings.AI_TIMEOUT

    async def _call_api(self, client: httpx.AsyncClient, model_name: str, system_prompt: str, user_prompt: str, temperature: float) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://biai.com.bd",
            "X-Title": "BIAI Corporate Lead Pipeline",
        }

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
        }

        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        response_schema: Optional[Type[BaseModel]] = None
    ) -> str:
        candidate_models = [self.model] + [m for m in FALLBACK_MODELS if m != self.model]
        last_error = None

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for candidate in candidate_models:
                try:
                    return await self._call_api(client, candidate, system_prompt, user_prompt, temperature)
                except Exception as e:
                    logger.warning(f"Model {candidate} failed: {e}. Trying fallback...")
                    last_error = e

        raise RuntimeError(f"All AI models failed. Last error: {last_error}")
