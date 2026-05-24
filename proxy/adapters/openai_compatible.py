import httpx
from .base import BaseAdapter


class OpenAICompatibleAdapter(BaseAdapter):
    """For OpenAI, DeepSeek, Groq — any OpenAI-format API."""

    @property
    def provider_name(self) -> str:
        return self.config.name

    async def chat(self, messages: list[dict], model: str, **params) -> dict:
        api_key = self.config.get_api_key()
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        body = {
            "model": model,
            "messages": messages,
        }
        if params.get("temperature") is not None:
            body["temperature"] = params["temperature"]
        if params.get("max_tokens") is not None:
            body["max_tokens"] = params["max_tokens"]
        if params.get("top_p") is not None:
            body["top_p"] = params["top_p"]

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                self.config.endpoint,
                headers=headers,
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()

        # Already in OpenAI format, normalize model name
        data["model"] = model
        return data
