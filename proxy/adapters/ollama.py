import httpx
from .base import BaseAdapter
from ..config import ProviderConfig


class OllamaAdapter(BaseAdapter):
    """Local Ollama — always OpenAI compatible, no API key needed."""

    def __init__(self, base_url: str, model: str, timeout: int = 60):
        dummy_config = ProviderConfig(
            name="ollama",
            endpoint=f"{base_url}/v1/chat/completions",
            api_key_env="",
            tags=["fallback"],
            models=[model],
        )
        super().__init__(dummy_config)
        self._model = model
        self._timeout = timeout

    @property
    def provider_name(self) -> str:
        return "ollama"

    async def chat(self, messages: list[dict], model: str = "", **params) -> dict:
        model = model or self._model

        body = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if params.get("temperature") is not None:
            body["temperature"] = params["temperature"]

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(self.config.endpoint, json=body)
            resp.raise_for_status()
            data = resp.json()

        data["model"] = model
        return data
