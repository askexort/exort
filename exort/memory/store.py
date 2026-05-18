"""
SQLite-backed memory store for conversation persistence.

Stores conversations and messages with full-text search support.
Each user/session gets its own conversation thread.
"""

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Optional

from exort.utils import generate_id, timestamp


class MemoryStore:
    """
    Persistent conversation memory using SQLite.

    Usage:
        store = MemoryStore()
        conv_id = store.create_conversation("My Chat")
        store.add_message(conv_id, "user", "Hello!")
        store.add_message(conv_id, "assistant", "Hi there!")
        history = store.get_history(conv_id)
    """

    def __init__(self, db_path: Optional[str] = None):
        from exort.config import get_exort_home
        if db_path is None:
            home = get_exort_home()
            home.mkdir(parents=True, exist_ok=True)
            db_path = str(home / "memory.db")
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _init_schema(self):
        """Create tables if they don't exist."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tool_calls TEXT,
                tool_call_id TEXT,
                name TEXT,
                timestamp TEXT NOT NULL,
                token_count INTEGER DEFAULT 0,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conv
                ON messages(conversation_id, id);

            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                content,
                content=messages,
                content_rowid=id
            );

            CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
                INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
            END;

            CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
                INSERT INTO messages_fts(messages_fts, rowid, content)
                VALUES('delete', old.id, old.content);
            END;

            CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE ON messages BEGIN
                INSERT INTO messages_fts(messages_fts, rowid, content)
                VALUES('delete', old.id, old.content);
                INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
            END;
        """)
        self._conn.commit()

    def create_conversation(self, title: str = "New Chat", metadata: dict = None) -> str:
        """Create a new conversation and return its ID."""
        conv_id = generate_id()
        now = timestamp()
        self._conn.execute(
            "INSERT INTO conversations (id, title, created_at, updated_at, metadata) VALUES (?, ?, ?, ?, ?)",
            (conv_id, title, now, now, json.dumps(metadata or {})),
        )
        self._conn.commit()
        return conv_id

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tool_calls: list = None,
        tool_call_id: str = None,
        name: str = None,
        token_count: int = 0,
    ):
        """Add a message to a conversation."""
        now = timestamp()
        self._conn.execute(
            "INSERT INTO messages (conversation_id, role, content, tool_calls, tool_call_id, name, timestamp, token_count) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                conversation_id,
                role,
                content,
                json.dumps(tool_calls) if tool_calls else None,
                tool_call_id,
                name,
                now,
                token_count,
            ),
        )
        self._conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id),
        )
        self._conn.commit()

    def get_history(
        self,
        conversation_id: str,
        limit: int = 50,
        include_tool: bool = True,
    ) -> list[dict]:
        """Get message history for a conversation."""
        query = "SELECT * FROM messages WHERE conversation_id = ?"
        params = [conversation_id]
        if not include_tool:
            query += " AND role IN ('user', 'assistant', 'system')"
        query += " ORDER BY id ASC"
        if limit:
            query += f" LIMIT {limit}"

        rows = self._conn.execute(query, params).fetchall()
        messages = []
        for row in rows:
            msg = {"role": row["role"], "content": row["content"]}
            if row["tool_calls"]:
                msg["tool_calls"] = json.loads(row["tool_calls"])
            if row["tool_call_id"]:
                msg["tool_call_id"] = row["tool_call_id"]
            if row["name"]:
                msg["name"] = row["name"]
            messages.append(msg)
        return messages

    def get_recent_conversations(self, limit: int = 20) -> list[dict]:
        """Get recent conversations."""
        rows = self._conn.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {
                "id": row["id"],
                "title": row["title"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    def search_messages(self, query: str, limit: int = 10) -> list[dict]:
        """Full-text search across all messages."""
        rows = self._conn.execute(
            "SELECT m.*, c.title as conv_title FROM messages m "
            "JOIN conversations c ON m.conversation_id = c.id "
            "WHERE messages_fts MATCH ? ORDER BY rank LIMIT ?",
            (query, limit),
        ).fetchall()
        return [
            {
                "conversation_id": row["conversation_id"],
                "conversation_title": row["conv_title"],
                "role": row["role"],
                "content": row["content"][:500],
                "timestamp": row["timestamp"],
            }
            for row in rows
        ]

    def delete_conversation(self, conversation_id: str):
        """Delete a conversation and all its messages."""
        self._conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        self._conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        self._conn.commit()

    def get_conversation_title(self, conversation_id: str) -> str:
        """Get the title of a conversation."""
        row = self._conn.execute(
            "SELECT title FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        return row["title"] if row else "Unknown"

    def update_title(self, conversation_id: str, title: str):
        """Update conversation title."""
        self._conn.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            (title, timestamp(), conversation_id),
        )
        self._conn.commit()

    def get_message_count(self, conversation_id: str) -> int:
        """Get total message count for a conversation."""
        row = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM messages WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
        return row["cnt"]

    def close(self):
        """Close the database connection."""
        self._conn.close()

    def __del__(self):
        try:
            self._conn.close()
        except Exception:
            pass
