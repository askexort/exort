"""
SQLite-backed conversation memory store.

Persists conversation history across sessions so the agent can
maintain context and recall previous interactions.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any


class MemoryStore:
    """SQLite-backed conversation memory.

    Stores conversation messages with metadata for retrieval and
    context management.

    Args:
        db_path: Path to the SQLite database file.
            Defaults to ``~/.openmind/memory.db``.

    Example::

        store = MemoryStore()
        store.add_message("conv-1", "user", "Hello!")
        store.add_message("conv-1", "assistant", "Hi there!")
        history = store.get_history("conv-1")
    """

    def __init__(self, db_path: str | None = None) -> None:
        if db_path is None:
            config_dir = Path.home() / ".openmind"
            config_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(config_dir / "memory.db")

        self.db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        """Create the database schema if it doesn't exist."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT,
                provider TEXT,
                model TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
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
                timestamp REAL NOT NULL,
                token_count INTEGER DEFAULT 0,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conversation
                ON messages(conversation_id, id);

            CREATE INDEX IF NOT EXISTS idx_conversations_updated
                ON conversations(updated_at DESC);
        """)
        self._conn.commit()

    def create_conversation(
        self,
        conversation_id: str,
        title: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Create a new conversation.

        Args:
            conversation_id: Unique conversation identifier.
            title: Optional human-readable title.
            provider: LLM provider used.
            model: LLM model used.
            metadata: Additional metadata dict.

        Returns:
            The conversation ID.
        """
        now = time.time()
        self._conn.execute(
            """INSERT OR REPLACE INTO conversations
               (id, title, provider, model, created_at, updated_at, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                conversation_id,
                title or f"Conversation {conversation_id[:8]}",
                provider,
                model,
                now,
                now,
                json.dumps(metadata or {}),
            ),
        )
        self._conn.commit()
        return conversation_id

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tool_calls: list[dict[str, Any]] | None = None,
        tool_call_id: str | None = None,
        name: str | None = None,
        token_count: int = 0,
    ) -> int:
        """Add a message to a conversation.

        Args:
            conversation_id: The conversation ID.
            role: Message role (system, user, assistant, tool).
            content: Message content.
            tool_calls: Tool call data (for assistant messages).
            tool_call_id: Tool call ID (for tool result messages).
            name: Tool name (for tool result messages).
            token_count: Token count for this message.

        Returns:
            The message row ID.
        """
        now = time.time()
        cursor = self._conn.execute(
            """INSERT INTO messages
               (conversation_id, role, content, tool_calls, tool_call_id,
                name, timestamp, token_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
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
        # Update conversation timestamp
        self._conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id),
        )
        self._conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def get_history(
        self,
        conversation_id: str,
        limit: int | None = None,
    ) -> list[dict[str, str]]:
        """Get conversation history in OpenAI message format.

        Args:
            conversation_id: The conversation ID.
            limit: Maximum number of messages to return (most recent).

        Returns:
            List of message dicts with ``role`` and ``content`` keys.
        """
        query = """
            SELECT role, content, tool_calls, tool_call_id, name
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
        """
        params: tuple = (conversation_id,)
        if limit:
            # Get the last N messages
            query = """
                SELECT role, content, tool_calls, tool_call_id, name
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id DESC
                LIMIT ?
            """
            params = (conversation_id, limit)

        rows = self._conn.execute(query, params).fetchall()

        if limit:
            rows = list(reversed(rows))

        messages: list[dict[str, str]] = []
        for row in rows:
            msg: dict[str, Any] = {
                "role": row["role"],
                "content": row["content"],
            }
            if row["tool_calls"]:
                msg["tool_calls"] = json.loads(row["tool_calls"])
            if row["tool_call_id"]:
                msg["tool_call_id"] = row["tool_call_id"]
            if row["name"]:
                msg["name"] = row["name"]
            messages.append(msg)

        return messages

    def get_conversations(self, limit: int = 50) -> list[dict[str, Any]]:
        """List recent conversations.

        Args:
            limit: Maximum conversations to return.

        Returns:
            List of conversation metadata dicts.
        """
        rows = self._conn.execute(
            """SELECT id, title, provider, model, created_at, updated_at,
                      metadata
               FROM conversations
               ORDER BY updated_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()

        return [
            {
                "id": row["id"],
                "title": row["title"],
                "provider": row["provider"],
                "model": row["model"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "metadata": json.loads(row["metadata"]),
            }
            for row in rows
        ]

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all its messages.

        Args:
            conversation_id: The conversation ID.

        Returns:
            True if the conversation was deleted.
        """
        cursor = self._conn.execute(
            "DELETE FROM conversations WHERE id = ?", (conversation_id,)
        )
        self._conn.execute(
            "DELETE FROM messages WHERE conversation_id = ?",
            (conversation_id,),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def get_token_usage(self, conversation_id: str) -> dict[str, int]:
        """Get total token usage for a conversation.

        Args:
            conversation_id: The conversation ID.

        Returns:
            Dict with ``total_tokens`` and ``message_count``.
        """
        row = self._conn.execute(
            """SELECT COALESCE(SUM(token_count), 0) as total,
                      COUNT(*) as count
               FROM messages
               WHERE conversation_id = ?""",
            (conversation_id,),
        ).fetchone()
        return {
            "total_tokens": row["total"],
            "message_count": row["count"],
        }

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def __enter__(self) -> MemoryStore:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"<MemoryStore db={self.db_path!r}>"
