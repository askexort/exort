"""
ConversationStore — SQLite-backed conversation memory.

Stores every session and message locally. Supports full-text search
so the engine can recall past conversations.
"""

import json
import os
import sqlite3
from pathlib import Path
from typing import Optional

from exort.utils import uid, now_iso


class ConversationStore:
    """
    Persistent message store.

        store = ConversationStore()
        sid = store.create("my chat")
        store.add(sid, "user", "hello")
        store.add(sid, "assistant", "hi!")
        history = store.messages(sid)
    """

    def __init__(self, path: Optional[str] = None):
        from exort.config import exort_dir
        if path is None:
            d = exort_dir()
            d.mkdir(parents=True, exist_ok=True)
            path = str(d / "conversations.db")
        self._path = path
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._migrate()

    def _migrate(self):
        self._db.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created TEXT NOT NULL,
                updated TEXT NOT NULL,
                meta TEXT DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tool_calls TEXT,
                tool_call_id TEXT,
                ts TEXT NOT NULL,
                tokens INTEGER DEFAULT 0,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );
            CREATE INDEX IF NOT EXISTS idx_msg_sess ON messages(session_id, id);
            CREATE VIRTUAL TABLE IF NOT EXISTS msg_fts USING fts5(content, content=messages, content_rowid=id);
            CREATE TRIGGER IF NOT EXISTS msg_ai AFTER INSERT ON messages BEGIN
                INSERT INTO msg_fts(rowid, content) VALUES (new.id, new.content);
            END;
            CREATE TRIGGER IF NOT EXISTS msg_ad AFTER DELETE ON messages BEGIN
                INSERT INTO msg_fts(msg_fts, rowid, content) VALUES('delete', old.id, old.content);
            END;
        """)
        self._db.commit()

    def create(self, title: str = "New session") -> str:
        sid = uid()
        t = now_iso()
        self._db.execute("INSERT INTO sessions VALUES (?,?,?,?,?)", (sid, title, t, t, "{}"))
        self._db.commit()
        return sid

    def add(self, session_id: str, role: str, content: str,
            tool_calls: list = None, tool_call_id: str = None, tokens: int = 0):
        t = now_iso()
        self._db.execute(
            "INSERT INTO messages (session_id,role,content,tool_calls,tool_call_id,ts,tokens) VALUES (?,?,?,?,?,?,?)",
            (session_id, role, content, json.dumps(tool_calls) if tool_calls else None,
             tool_call_id, t, tokens),
        )
        self._db.execute("UPDATE sessions SET updated=? WHERE id=?", (t, session_id))
        self._db.commit()

    def messages(self, session_id: str, limit: int = 50) -> list[dict]:
        rows = self._db.execute(
            "SELECT * FROM messages WHERE session_id=? ORDER BY id ASC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        out = []
        for r in rows:
            m = {"role": r["role"], "content": r["content"]}
            if r["tool_calls"]:
                m["tool_calls"] = json.loads(r["tool_calls"])
            if r["tool_call_id"]:
                m["tool_call_id"] = r["tool_call_id"]
            out.append(m)
        return out

    def recent(self, limit: int = 20) -> list[dict]:
        rows = self._db.execute("SELECT * FROM sessions ORDER BY updated DESC LIMIT ?", (limit,)).fetchall()
        return [{"id": r["id"], "title": r["title"], "updated": r["updated"]} for r in rows]

    def search(self, query: str, limit: int = 10) -> list[dict]:
        rows = self._db.execute(
            "SELECT m.*, s.title FROM messages m JOIN sessions s ON m.session_id=s.id "
            "WHERE msg_fts MATCH ? ORDER BY rank LIMIT ?", (query, limit),
        ).fetchall()
        return [{"session": r["session_id"], "title": r["title"],
                 "role": r["role"], "snippet": r["content"][:300]} for r in rows]

    def delete(self, session_id: str):
        self._db.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
        self._db.execute("DELETE FROM sessions WHERE id=?", (session_id,))
        self._db.commit()

    def title(self, session_id: str) -> str:
        r = self._db.execute("SELECT title FROM sessions WHERE id=?", (session_id,)).fetchone()
        return r["title"] if r else "?"

    def close(self):
        self._db.close()
