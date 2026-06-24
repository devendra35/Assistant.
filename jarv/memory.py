import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import DB_PATH, MAX_MEMORY_ITEMS, CONTEXT_WINDOW

logger = logging.getLogger("astrax.memory")
class Memory:

    def __init__(self):
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()
        logger.info("Memory module online.")

    def _init_schema(self):
        cur = self.conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                role        TEXT    NOT NULL,
                content     TEXT    NOT NULL,
                timestamp   TEXT    NOT NULL,
                session_id  TEXT    NOT NULL DEFAULT 'default'
            );

            CREATE TABLE IF NOT EXISTS facts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                key         TEXT    UNIQUE NOT NULL,
                value       TEXT    NOT NULL,
                updated_at  TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT    NOT NULL,
                status      TEXT    NOT NULL DEFAULT 'pending',
                created_at  TEXT    NOT NULL,
                done_at     TEXT
            );
        """)
        self.conn.commit()
        def add_message(self, role: str, content: str, session_id: str = "default"):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO conversations (role, content, timestamp, session_id) VALUES (?, ?, ?, ?)",
            (role, content, datetime.utcnow().isoformat(), session_id),
        )
        self.conn.commit()
        self._trim_history()
         def get_context(self, session_id: str = "default") -> list[dict]:
        cur = self.conn.cursor()
        cur.execute(
            """SELECT role, content FROM conversations
               WHERE session_id = ?
               ORDER BY id DESC LIMIT ?""",
            (session_id, CONTEXT_WINDOW),
        )
        rows = cur.fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    def clear_history(self, session_id: str = "default"):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
        self.conn.commit()
        logger.info("Conversation history cleared.")

    def _trim_history(self):
        cur = self.conn.cursor()
        cur.execute(
            """DELETE FROM conversations WHERE id IN (
                SELECT id FROM conversations ORDER BY id ASC
                LIMIT MAX(0, (SELECT COUNT(*) FROM conversations) - ?)
            )""",
            (MAX_MEMORY_ITEMS,),
        )
        self.conn.commit()

    def remember(self, key: str, value: str):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO facts(key, value, updated_at) VALUES(?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key.lower(), value, datetime.utcnow().isoformat()),
        )
        self.conn.commit()

    def recall(self, key: str) -> str | None:
        cur = self.conn.cursor()
        cur.execute("SELECT value FROM facts WHERE key = ?", (key.lower(),))
        row = cur.fetchone()
        return row["value"] if row else None

    def get_all_facts(self) -> dict:
        cur = self.conn.cursor()
        cur.execute("SELECT key, value FROM facts")
        return {r["key"]: r["value"] for r in cur.fetchall()}

    def add_task(self, description: str) -> int:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO tasks(description, created_at) VALUES(?, ?)",
            (description, datetime.utcnow().isoformat()),
        )
        self.conn.commit()
        return cur.lastrowid
         def complete_task(self, task_id: int):
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE tasks SET status='done', done_at=? WHERE id=?",
            (datetime.utcnow().isoformat(), task_id),
        )
        self.conn.commit()

    def get_pending_tasks(self) -> list[dict]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM tasks WHERE status='pending' ORDER BY id")
        return [dict(r) for r in cur.fetchall()]

    def __del__(self):
        try:
            self.conn.close()
        except Exception:
            pass



