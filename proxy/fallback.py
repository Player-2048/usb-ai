"""
Fallback engine — when an external AI fails, degrade gracefully.

Degradation order:
1. Retry same provider once
2. Try next provider with matching tags
3. Fall back to local Ollama
4. Return error if Ollama also unavailable
"""

import time
import logging
from .config import AppConfig, ProviderConfig
from .adapters.ollama import OllamaAdapter

logger = logging.getLogger(__name__)


class FallbackEngine:
    def __init__(self, config: AppConfig):
        self.config = config
        self.ollama = OllamaAdapter(
            base_url=config.ollama_base_url,
            model=config.ollama_model,
            timeout=config.ollama_timeout,
        )
        self.providers: dict[str, ProviderConfig] = {
            p.name: p for p in config.providers
        }

    async def try_with_fallback(
        self,
        messages: list[dict],
        primary_provider: str,
        primary_model: str,
        adapter_factory,
        **params,
    ) -> dict:
        """
        Try primary provider, then degrade through alternatives.
        Returns a dict with keys: response (OpenAI format), provider_used, model_used,
        degraded (bool), error (str or None).
        """
        tried = set()

        # Tier 1: primary provider
        result = await self._try_provider(
            primary_provider, primary_model, messages, adapter_factory, **params
        )
        if result:
            result["degraded"] = False
            return result
        tried.add(primary_provider)

        # Tier 2: same-tag providers
        primary_config = self.providers.get(primary_provider)
        if primary_config:
            primary_tags = set(primary_config.tags)
            for provider_name, provider_config in self.providers.items():
                if provider_name in tried:
                    continue
                if set(provider_config.tags) & primary_tags:
                    model = provider_config.models[0] if provider_config.models else primary_model
                    result = await self._try_provider(
                        provider_name, model, messages, adapter_factory, **params
                    )
                    if result:
                        result["degraded"] = True
                        return result
                    tried.add(provider_name)

        # Tier 2.5: try any remaining providers
        for provider_name, provider_config in self.providers.items():
            if provider_name in tried:
                continue
            model = provider_config.models[0] if provider_config.models else primary_model
            result = await self._try_provider(
                provider_name, model, messages, adapter_factory, **params
            )
            if result:
                result["degraded"] = True
                return result
            tried.add(provider_name)

        # Tier 3: local Ollama fallback
        result = await self._try_ollama(messages, **params)
        if result:
            result["degraded"] = True
            return result

        # Tier 4: complete failure
        return {
            "response": {
                "id": "fallback-error",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": "none",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "[公共协议] 所有外部 AI 和本地模型均不可用，请检查网络连接和 Ollama 服务状态。",
                    },
                    "finish_reason": "error",
                }],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            },
            "provider_used": "none",
            "model_used": "none",
            "degraded": True,
            "error": "All providers and fallback failed",
        }

    async def _try_provider(self, name, model, messages, adapter_factory, **params):
        try:
            adapter = adapter_factory(name)
            resp = await adapter.chat(messages, model, **params)
            return {
                "response": resp,
                "provider_used": name,
                "model_used": model,
            }
        except Exception as e:
            logger.warning(f"Provider {name} failed: {e}")
            return None

    async def _try_ollama(self, messages, **params):
        try:
            resp = await self.ollama.chat(messages, **params)
            # Prepend degradation notice
            if resp.get("choices"):
                content = resp["choices"][0]["message"]["content"]
                resp["choices"][0]["message"]["content"] = (
                    "[公共协议低速供电模式] 外部 AI 不可用，当前由本地 AI 响应：\n\n" + content
                )
            return {
                "response": resp,
                "provider_used": "ollama",
                "model_used": self.config.ollama_model,
            }
        except Exception as e:
            logger.warning(f"Ollama fallback failed: {e}")
            return None
