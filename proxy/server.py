import time
import uuid
import logging
from contextlib import asynccontextmanager

import webbrowser
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import load_config, resolve_path
from .router import Router
from .fallback import FallbackEngine
from .logger import Logger
from .memory import Memory
from .adapters.openai_compatible import OpenAICompatibleAdapter
from .adapters.anthropic import AnthropicAdapter
from .adapters.gemini import GeminiAdapter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("proxy")

config = load_config()

router = Router(config)
fallback = FallbackEngine(config)
db = Logger(config.sqlite_path)
memory = Memory(config.chroma_path)

ANTHROPIC_PROVIDER = {"claude", "anthropic"}
GEMINI_PROVIDER = {"gemini", "google"}


def _adapter_factory(name: str):
    provider = router.get_provider(name)
    if not provider:
        raise RuntimeError(f"Unknown provider: {name}")
    if name in ANTHROPIC_PROVIDER:
        return AnthropicAdapter(provider)
    if name in GEMINI_PROVIDER:
        return GeminiAdapter(provider)
    return OpenAICompatibleAdapter(provider)


@asynccontextmanager
async def lifespan(app: FastAPI):
    url = f"http://127.0.0.1:{config.server_port}"
    logger.info(f"AI Proxy starting on {config.server_host}:{config.server_port}")
    logger.info(f"Default: {config.default_provider}/{config.default_model}")
    logger.info(f"Ollama: {config.ollama_model} @ {config.ollama_base_url}")
    logger.info(f"Providers: {[p.name for p in config.providers]}")
    logger.info(f"Opening {url} in browser...")
    try:
        webbrowser.open(url)
    except Exception:
        logger.warning("Could not open browser automatically")
    yield
    logger.info("AI Proxy shutting down")


app = FastAPI(title="AI Proxy", version="0.1.0", lifespan=lifespan)

# Serve frontend
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    html_path = STATIC_DIR / "index.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Personal AI</h1><p>Frontend not found.</p>")


@app.get("/settings")
async def settings_page():
    """Serve the settings page."""
    settings_path = STATIC_DIR / "settings.html"
    if settings_path.exists():
        return HTMLResponse(content=settings_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Settings</h1><p>Settings page not found.</p>")


@app.get("/v1/export")
async def export_data():
    """Export all data as a downloadable zip."""
    import json, zipfile, io, tempfile, shutil, uuid

    buf = io.BytesIO()
    db_path = Path(resolve_path(config.sqlite_path))
    chroma_path = Path(resolve_path(config.chroma_path))

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # SQLite
        if db_path.exists():
            zf.write(db_path, "data/logs.db")

        # ChromaDB
        if chroma_path.exists():
            for item in chroma_path.rglob("*"):
                if item.is_file():
                    zf.write(item, f"data/chroma/{item.relative_to(chroma_path)}")

        # config
        config_yaml = Path(__file__).parent.parent / "config.yaml"
        if config_yaml.exists():
            zf.write(config_yaml, "config.yaml")

    from fastapi.responses import StreamingResponse
    ts = int(time.time())
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=personal-ai-export-{ts}.zip",
            "Content-Length": str(buf.tell()),
        },
    )


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    model = body.get("model", config.default_model)
    x_router = body.get("x-router")
    x_custom = body.get("x-custom")

    if not messages:
        raise HTTPException(status_code=400, detail="messages is required")

    request_id = f"req_{uuid.uuid4().hex[:12]}"

    # Custom provider: bypass routing, call directly
    if x_custom and isinstance(x_custom, dict):
        endpoint = x_custom.get("endpoint")
        api_key = x_custom.get("api_key")
        custom_model = x_custom.get("model", model)
        custom_name = x_custom.get("name", "custom")

        if not endpoint:
            raise HTTPException(status_code=400, detail="x-custom.endpoint is required")

        logger.info(f"[{request_id}] -> custom/{custom_name} @ {endpoint}")

        import httpx
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        outbound_body = {
            "model": custom_model,
            "messages": messages,
        }
        for key in ("temperature", "max_tokens", "top_p"):
            if key in body:
                outbound_body[key] = body[key]

        db.log_request(request_id, messages, provider=custom_name, model=custom_model, tags="custom")
        start = time.time()

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(endpoint, headers=headers, json=outbound_body)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            elapsed_ms = int((time.time() - start) * 1000)
            db.log_response(request_id, {}, elapsed_ms, str(e))
            raise HTTPException(status_code=502, detail=f"Custom provider error: {e}")

        elapsed_ms = int((time.time() - start) * 1000)
        data["model"] = custom_model
        db.log_response(request_id, data, elapsed_ms, None)
        return JSONResponse(content=data)

    # Route
    provider_config, resolved_model = router.resolve(messages, model, x_router)
    logger.info(
        f"[{request_id}] → {provider_config.name}/{resolved_model}"
        + (f" (override: {x_router})" if x_router else "")
    )

    # Extract params
    extra_params = {}
    for key in ("temperature", "max_tokens", "top_p"):
        if key in body:
            extra_params[key] = body[key]

    tags = ",".join(provider_config.tags)

    # Log request
    db.log_request(
        request_id=request_id,
        messages=messages,
        provider=provider_config.name,
        model=resolved_model,
        tags=tags,
    )

    # Execute with fallback
    start = time.time()
    result = await fallback.try_with_fallback(
        messages=messages,
        primary_provider=provider_config.name,
        primary_model=resolved_model,
        adapter_factory=_adapter_factory,
        **extra_params,
    )
    elapsed_ms = int((time.time() - start) * 1000)

    response_body = result["response"]
    error = result.get("error")
    actual_provider = result.get("provider_used", provider_config.name)

    # Log response
    db.log_response(request_id, response_body, elapsed_ms, error)

    # Add to memory
    try:
        memory.add(request_id, messages, response_body)
    except Exception as e:
        logger.warning(f"Memory add failed: {e}")

    # Inject degradation status into response for transparency
    if result.get("degraded"):
        response_body["x-degraded"] = True
        response_body["x-provider-used"] = actual_provider

    return JSONResponse(content=response_body)


@app.get("/v1/models")
async def list_models():
    models = []
    for provider in config.providers:
        for model in provider.models:
            models.append({
                "id": model,
                "object": "model",
                "owned_by": provider.name,
            })
    # Include Ollama fallback
    models.append({
        "id": f"@ollama/{config.ollama_model}",
        "object": "model",
        "owned_by": "ollama",
    })
    return {"object": "list", "data": models}


@app.get("/health")
async def health():
    return {"status": "ok", "ollama_model": config.ollama_model}


@app.get("/v1/history")
async def history_search(query: str = "", limit: int = 20, tag: str = ""):
    """Search past conversations by keyword or semantic match."""
    if tag:
        records = db.search_by_tags(tag, limit)
        return {"results": records}
    elif query:
        results = memory.search(query, limit)
        enriched = []
        for r in results:
            req = db.get_request(r["request_id"])
            if req:
                req["similarity"] = 1 - r["distance"]
                enriched.append(req)
        return {"results": enriched}
    else:
        records = db.query_recent(limit)
        return {"results": records}


@app.get("/v1/history/recent")
async def recent_history(limit: int = 20):
    records = db.query_recent(limit)
    return {"results": records}


@app.get("/stats")
async def stats():
    return db.get_stats()
