from abc import ABC, abstractmethod
from ..config import ProviderConfig


class BaseAdapter(ABC):
    def __init__(self, config: ProviderConfig):
        self.config = config

    @abstractmethod
    async def chat(self, messages: list[dict], model: str, **params) -> dict:
        """Send chat request, return OpenAI-format response dict."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...
