"""
Routing engine — decides which provider handles a request.

Priority (highest first):
1. x-router field in request body (manual override)
2. model field prefix mapping (e.g. @claude/sonnet, claude-sonnet-4-6)
3. Tag-based keyword matching on message content
4. Default provider
"""

import re
from .config import AppConfig, ProviderConfig


MODEL_PREFIX_MAP = {
    "claude": "claude",
    "gpt": "openai",
    "o1": "openai",
    "o3": "openai",
    "o4": "openai",
    "deepseek": "deepseek",
    "groq": "groq",
    "gemini": "gemini",
    "llama": "groq",
    "mixtral": "groq",
}

PROVIDER_PREFIX_RE = re.compile(r"^@(\w+)/(.+)")


class Router:
    def __init__(self, config: AppConfig):
        self.config = config
        self.providers: dict[str, ProviderConfig] = {
            p.name: p for p in config.providers
        }
        self.default_provider = config.default_provider
        self.default_model = config.default_model

    def resolve(
        self,
        messages: list[dict],
        model: str = "",
        x_router: dict | None = None,
    ) -> tuple[ProviderConfig, str]:
        """
        Returns (provider_config, model_name).
        """

        # 1. Manual override via x-router
        if x_router:
            provider_name = x_router.get("provider", "")
            override_model = x_router.get("model", model)
            if provider_name in self.providers:
                return self.providers[provider_name], override_model

        # 2. @provider/model prefix
        if model.startswith("@"):
            m = PROVIDER_PREFIX_RE.match(model)
            if m:
                provider_name = m.group(1)
                real_model = m.group(2)
                if provider_name in self.providers:
                    return self.providers[provider_name], real_model

        # 3. Model name prefix matching
        model_lower = model.lower()
        for prefix, provider_name in MODEL_PREFIX_MAP.items():
            if model_lower.startswith(prefix):
                if provider_name in self.providers:
                    return self.providers[provider_name], model
                break

        # 4. Tag-based routing from message content
        combined = " ".join(
            m.get("content", "") for m in messages
            if isinstance(m.get("content"), str)
        ).lower()

        for rule in self.config.routing_rules:
            for tag in rule.tags:
                if tag.lower() in combined:
                    if rule.provider in self.providers:
                        return self.providers[rule.provider], model

        # 5. Default provider
        if self.default_provider in self.providers:
            return self.providers[self.default_provider], model or self.default_model

        # Absolute fallback — first available provider
        if self.providers:
            first = list(self.providers.values())[0]
            return first, model or first.models[0] if first.models else "default"

        raise RuntimeError("No providers configured")

    def get_provider(self, name: str) -> ProviderConfig | None:
        return self.providers.get(name)
