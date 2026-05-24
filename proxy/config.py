import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


@dataclass
class ProviderConfig:
    name: str
    endpoint: str
    api_key_env: str
    tags: list = field(default_factory=list)
    models: list = field(default_factory=list)

    def get_api_key(self) -> Optional[str]:
        return os.getenv(self.api_key_env)


@dataclass
class RoutingRule:
    tags: list
    provider: str


@dataclass
class AppConfig:
    server_host: str = "127.0.0.1"
    server_port: int = 8080
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_timeout: int = 60
    providers: list[ProviderConfig] = field(default_factory=list)
    default_provider: str = "openai"
    default_model: str = "gpt-4o-mini"
    routing_rules: list[RoutingRule] = field(default_factory=list)
    sqlite_path: str = "./data/logs.db"
    chroma_path: str = "./data/chroma"


def load_config() -> AppConfig:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config not found: {CONFIG_PATH}")

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    config = AppConfig()

    if "server" in raw:
        config.server_host = raw["server"].get("host", config.server_host)
        config.server_port = raw["server"].get("port", config.server_port)

    if "ollama" in raw:
        config.ollama_base_url = raw["ollama"].get("base_url", config.ollama_base_url)
        config.ollama_model = raw["ollama"].get("model", config.ollama_model)
        config.ollama_timeout = raw["ollama"].get("timeout", config.ollama_timeout)

    if "providers" in raw:
        for p in raw["providers"]:
            config.providers.append(ProviderConfig(
                name=p["name"],
                endpoint=p["endpoint"],
                api_key_env=p.get("api_key_env", ""),
                tags=p.get("tags", []),
                models=p.get("models", []),
            ))

    config.default_provider = raw.get("default_provider", config.default_provider)
    config.default_model = raw.get("default_model", config.default_model)

    if "routing" in raw and "rules" in raw["routing"]:
        for r in raw["routing"]["rules"]:
            config.routing_rules.append(RoutingRule(
                tags=r.get("tags", []),
                provider=r["provider"],
            ))

    if "database" in raw:
        config.sqlite_path = raw["database"].get("sqlite_path", config.sqlite_path)
        config.chroma_path = raw["database"].get("chroma_path", config.chroma_path)

    return config


def resolve_path(relative: str) -> Path:
    base = Path(__file__).parent.parent
    p = base / relative
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
