import httpx
from .base import BaseAdapter
from ..translator import openai_to_anthropic, anthropic_to_openai


class AnthropicAdapter(BaseAdapter):
    @property
    def provider_name(self) -> str:
        return self.config.name

    async def chat(self, messages: list[dict], model: str, **params) -> dict:
        api_key = self.config.get_api_key()
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key or "",
            "anthropic-version": "2023-06-01",
        }

        body = openai_to_anthropic(messages, model, **params)

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                self.config.endpoint,
                headers=headers,
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()

        return anthropic_to_openai(data, model)
