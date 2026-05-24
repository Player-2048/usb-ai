"""
CLI for querying history and replaying requests.

Usage:
  ai-proxy history --today
  ai-proxy history --date 2026-05-14
  ai-proxy history --search "database"
  ai-proxy history --recent
  ai-proxy stats
  ai-proxy replay <request_id>
  ai-proxy replay --db-id <id>
"""

import json
import sys
import click

from .config import load_config
from .logger import Logger
from .memory import Memory
from .adapters.openai_compatible import OpenAICompatibleAdapter
from .adapters.anthropic import AnthropicAdapter
from .adapters.gemini import GeminiAdapter
from .router import Router

config = load_config()
db = Logger(config.sqlite_path)
memory = Memory(config.chroma_path)
router = Router(config)

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


def _format_request(r: dict) -> str:
    """Format a single request record for display."""
    ts = r.get("timestamp", "")
    provider = r.get("provider", "?")
    model = r.get("model", "?")
    source = r.get("source", "?")
    request_id = r.get("request_id", "")
    duration = r.get("duration_ms", "")
    error = r.get("error", "")
    tags = r.get("tags", "")

    msgs = json.loads(r.get("messages_json", "[]"))
    preview = ""
    for m in msgs:
        if m.get("role") == "user":
            preview = m.get("content", "")[:80]
            break

    lines = [
        f"━━ [{request_id}] {ts}",
        f"   Provider: {provider}  Model: {model}  Source: {source}  Duration: {duration}ms",
    ]
    if tags:
        lines.append(f"   Tags: {tags}")
    if preview:
        lines.append(f"   Query: {preview}...")
    if error:
        lines.append(f"   ERROR: {error}")

    return "\n".join(lines)


def _show_table(records: list[dict]):
    if not records:
        click.echo("No records found.")
        return
    for r in records:
        click.echo(_format_request(r))
        click.echo()
    click.echo(f"Total: {len(records)} record(s)")


@click.group()
def cli():
    """AI Proxy — history query and replay tool."""
    pass


@cli.command()
@click.option("--today", is_flag=True, help="Show today's requests")
@click.option("--date", default=None, help="Show requests for a specific date (YYYY-MM-DD)")
@click.option("--search", default=None, help="Semantic search by query text")
@click.option("--tag", default=None, help="Filter by tag")
@click.option("--recent", is_flag=True, help="Show recent requests")
@click.option("--limit", default=50, help="Max results (default: 50)")
def history(today, date, search, tag, recent, limit):
    """Query request history."""
    if today:
        from datetime import date as dt
        date = dt.today().isoformat()
        records = db.query_by_date(date, limit)
        _show_table(records)
    elif date:
        records = db.query_by_date(date, limit)
        _show_table(records)
    elif search:
        results = memory.search(search, limit)
        if not results:
            click.echo("No semantic matches found.")
            return
        for r in results:
            req = db.get_request(r["request_id"])
            if req:
                click.echo(_format_request(req))
                click.echo(f"   Similarity: {1 - r['distance']:.3f}")
                click.echo()
    elif tag:
        records = db.search_by_tags(tag, limit)
        _show_table(records)
    elif recent:
        records = db.query_recent(limit)
        _show_table(records)
    else:
        records = db.query_recent(limit)
        _show_table(records)


@cli.command()
@click.argument("request_id", required=False)
@click.option("--db-id", type=int, default=None, help="Replay by database row ID")
@click.option("--dry-run", is_flag=True, help="Show what would be sent without executing")
def replay(request_id, db_id, dry_run):
    """Replay a past request."""
    if db_id:
        req = db.get_request_by_db_id(db_id)
    elif request_id:
        req = db.get_request(request_id)
    else:
        click.echo("Provide a request_id or --db-id")
        sys.exit(1)

    if not req:
        click.echo("Request not found.")
        sys.exit(1)

    messages = json.loads(req["messages_json"])
    provider_name = req["provider"]
    model = req["model"]
    source = req["source"]

    click.echo(f"Replaying [{req['request_id']}]")
    click.echo(f"  Provider: {provider_name}  Model: {model}  Source: {source}")
    click.echo(f"  Original time: {req['timestamp']}")

    for m in messages:
        role = m.get("role", "?")
        content = m.get("content", "")
        click.echo(f"  [{role}] {content[:100]}")

    if dry_run:
        click.echo("\n[Dry run — not executing]")
        return

    click.echo("\nSending replay...")
    import asyncio

    async def _replay():
        adapter = _adapter_factory(provider_name)
        return await adapter.chat(messages, model)

    try:
        result = asyncio.run(_replay())
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        click.echo(f"\nResponse:\n{content}")

        # Log replay
        import uuid
        replay_id = f"rep_{uuid.uuid4().hex[:12]}"
        db.log_request(
            request_id=replay_id,
            messages=messages,
            provider=provider_name,
            model=model,
            tags=req.get("tags", ""),
            replayed_from=req["id"],
        )
        usage = result.get("usage", {})
        db.log_response(replay_id, result, 0, None)
        click.echo(f"\nReplay logged as [{replay_id}]")
    except Exception as e:
        click.echo(f"Replay failed: {e}")
        sys.exit(1)


@cli.command()
def stats():
    """Show usage statistics."""
    s = db.get_stats()
    click.echo("=== AI Proxy Statistics ===")
    click.echo(f"Total requests: {s['total_requests']}")
    click.echo(f"Errors:         {s['errors']}")
    click.echo(f"Avg duration:   {s['avg_duration_ms']}ms")
    click.echo()
    click.echo("By provider:")
    for provider, count in s["by_provider"].items():
        click.echo(f"  {provider}: {count}")
    click.echo()
    click.echo("By source:")
    for source, count in s["by_source"].items():
        click.echo(f"  {source}: {count}")


if __name__ == "__main__":
    cli()
