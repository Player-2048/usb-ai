import sqlite3
import json
import time
from datetime import datetime, timezone
from typing import Optional
from .config import resolve_path

SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT UNIQUE NOT NULL,
    timestamp TEXT NOT NULL,
    provider TEXT,
    model TEXT,
    source TEXT NOT NULL DEFAULT 'external',
    messages_json TEXT NOT NULL,
    response_json TEXT,
    tags TEXT,
    duration_ms INTEGER,
    error TEXT,
    replayed_from INTEGER REFERENCES requests(id)
);

CREATE INDEX IF NOT EXISTS idx_requests_timestamp ON requests(timestamp);
CREATE INDEX IF NOT EXISTS idx_requests_provider ON requests(provider);
CREATE INDEX IF NOT EXISTS idx_requests_source ON requests(source);
CREATE INDEX IF NOT EXISTS idx_requests_tags ON requests(tags);
"""


class Logger:
    def __init__(self, db_path: str):
        self.db_path = str(resolve_path(db_path))
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        conn = self._get_conn()
        conn.executescript(SCHEMA)
        conn.commit()
        conn.close()

    def log_request(
        self,
        request_id: str,
        messages: list[dict],
        provider: Optional[str] = None,
        model: Optional[str] = None,
        tags: Optional[str] = None,
        replayed_from: Optional[int] = None,
    ) -> int:
        conn = self._get_conn()
        cursor = conn.execute(
            """INSERT INTO requests (request_id, timestamp, provider, model, source,
               messages_json, tags, replayed_from)
               VALUES (?, ?, ?, ?, 'external', ?, ?, ?)""",
            (
                request_id,
                datetime.now(timezone.utc).isoformat(),
                provider,
                model,
                json.dumps(messages, ensure_ascii=False),
                tags,
                replayed_from,
            ),
        )
        conn.commit()
        row_id = cursor.lastrowid
        conn.close()
        return row_id

    def log_response(self, request_id: str, response: dict, duration_ms: int, error: Optional[str] = None):
        conn = self._get_conn()
        conn.execute(
            """UPDATE requests SET response_json = ?, duration_ms = ?, error = ?
               WHERE request_id = ?""",
            (
                json.dumps(response, ensure_ascii=False) if response else None,
                duration_ms,
                error,
                request_id,
            ),
        )
        conn.commit()
        conn.close()

    def get_request(self, request_id: str) -> Optional[dict]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM requests WHERE request_id = ?", (request_id,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_request_by_db_id(self, db_id: int) -> Optional[dict]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM requests WHERE id = ?", (db_id,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def query_by_date(self, date_str: str, limit: int = 50) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM requests WHERE timestamp LIKE ? ORDER BY timestamp DESC LIMIT ?",
            (f"{date_str}%", limit),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def query_recent(self, limit: int = 50) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM requests ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_stats(self) -> dict:
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) as c FROM requests").fetchone()["c"]
        by_provider = conn.execute(
            "SELECT provider, COUNT(*) as c FROM requests GROUP BY provider ORDER BY c DESC"
        ).fetchall()
        by_source = conn.execute(
            "SELECT source, COUNT(*) as c FROM requests GROUP BY source ORDER BY c DESC"
        ).fetchall()
        errors = conn.execute(
            "SELECT COUNT(*) as c FROM requests WHERE error IS NOT NULL"
        ).fetchone()["c"]
        avg_duration = conn.execute(
            "SELECT AVG(duration_ms) as avg FROM requests WHERE duration_ms IS NOT NULL"
        ).fetchone()["avg"]
        conn.close()
        return {
            "total_requests": total,
            "errors": errors,
            "avg_duration_ms": round(avg_duration, 1) if avg_duration else 0,
            "by_provider": {r["provider"]: r["c"] for r in by_provider},
            "by_source": {r["source"]: r["c"] for r in by_source},
        }

    def search_by_tags(self, tag: str, limit: int = 50) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM requests WHERE tags LIKE ? ORDER BY timestamp DESC LIMIT ?",
            (f"%{tag}%", limit),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
