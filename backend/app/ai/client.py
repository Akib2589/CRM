# app/ai/client.py
from app.ai.provider import AIProvider, OpenAICompatibleProvider
from app.core.config import settings

_provider_instance: AIProvider | None = None

def get_ai_provider() -> AIProvider:
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = OpenAICompatibleProvider(
            api_key=settings.AI_API_KEY,
            base_url=settings.AI_BASE_URL,
            model=settings.AI_MODEL,
            timeout=settings.AI_TIMEOUT
        )
    return _provider_instance
