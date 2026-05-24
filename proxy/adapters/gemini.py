import httpx
from .base import BaseAdapter
from ..translator import openai_to_gemini, gemini_to_openai


class GeminiAdapter(BaseAdapter):
    @property
    def provider_name(self) -> str:
        return self.config.name

    async def chat(self, messages: list[dict], model: str, **params) -> dict:
        api_key = self.config.get_api_key()

        body = openai_to_gemini(messages, model, **params)

        url = f"{self.config.endpoint}/{model}:generateContent"
        if api_key:
            url += f"?key={api_key}"

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=body)
            resp.raise_for_status()
            data = resp.json()

        return gemini_to_openai(data, model)
