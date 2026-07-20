"""Audit logging service — persists API requests to SQLite with batched writes."""

import sqlite3
from datetime import datetime
from contextlib import closing
from pathlib import Path
from typing import List, Optional
import threading

_audit_queue = []
_audit_lock = threading.Lock()
_audit_db_path: Optional[Path] = None

def init_audit_db(db_path: Path):
    global _audit_db_path
    _audit_db_path = db_path
    _audit_db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(str(_audit_db_path))) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_id TEXT,
                user_role TEXT,
                action TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                method TEXT NOT NULL,
                ip_address TEXT,
                status_code INTEGER,
                duration_ms REAL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id)")
        conn.commit()

def log_audit_entry(user_id: str, user_role: str, action: str, endpoint: str,
                    method: str, ip_address: str, status_code: int,
                    duration_ms: float):
    entry = (datetime.utcnow().isoformat(), user_id, user_role, action,
             endpoint, method, ip_address, status_code, duration_ms)
    with _audit_lock:
        _audit_queue.append(entry)
    _flush_queue()

def _flush_queue():
    if _audit_db_path is None or not _audit_queue:
        return
    with _audit_lock:
        entries = _audit_queue[:100]
        del _audit_queue[:100]
    if not entries:
        return
    try:
        with closing(sqlite3.connect(str(_audit_db_path))) as conn:
            conn.executemany(
                """INSERT INTO audit_log
                   (timestamp, user_id, user_role, action, endpoint, method,
                    ip_address, status_code, duration_ms)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", entries)
            conn.commit()
    except Exception as e:
        with _audit_lock:
            _audit_queue.extend(entries)

def get_audit_logs(limit: int = 100, offset: int = 0,
                   user_id: Optional[str] = None, action: Optional[str] = None,
                   start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[dict]:
    if _audit_db_path is None:
        return []
    with closing(sqlite3.connect(str(_audit_db_path))) as conn:
        conn.row_factory = sqlite3.Row
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if action:
            query += " AND action = ?"
            params.append(action)
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        return [dict(row) for row in conn.execute(query, params).fetchall()]

def get_audit_stats() -> dict:
    if _audit_db_path is None:
        return {}
    with closing(sqlite3.connect(str(_audit_db_path))) as conn:
        conn.row_factory = sqlite3.Row
        total = conn.execute("SELECT COUNT(*) as cnt FROM audit_log").fetchone()["cnt"]
        by_action = conn.execute(
            "SELECT action, COUNT(*) as cnt FROM audit_log GROUP BY action ORDER BY cnt DESC"
        ).fetchall()
        by_user = conn.execute(
            "SELECT user_id, COUNT(*) as cnt FROM audit_log GROUP BY user_id ORDER BY cnt DESC LIMIT 10"
        ).fetchall()
        by_endpoint = conn.execute(
            "SELECT endpoint, COUNT(*) as cnt FROM audit_log GROUP BY endpoint ORDER BY cnt DESC LIMIT 10"
        ).fetchall()
        return {
            "total_entries": total,
            "by_action": [dict(r) for r in by_action],
            "by_user": [dict(r) for r in by_user],
            "by_endpoint": [dict(r) for r in by_endpoint],
        }
