"""
Token tracker data store — JSON-backed persistence for tracked tokens.

Each entry maps a (chat_id, token_address) pair to tracking metadata.
Groups and private chats are both supported.
"""

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger("openmind-tracker")

DATA_DIR = Path(__file__).parent / "data"
STORE_FILE = DATA_DIR / "tracked_tokens.json"


class TrackerStore:
    """Persistent store for tracked tokens per user/chat."""

    def __init__(self, path: Path = STORE_FILE):
        self.path = path
        self._data: dict = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            try:
                with open(self.path) as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                logger.error(f"Failed to load tracker store: {e}")
        return {"tracked": {}}

    def _save(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self._data, f, indent=2)

    def _key(self, chat_id: int, token_address: str) -> str:
        return f"{chat_id}:{token_address.lower()}"

    def add_token(
        self,
        chat_id: int,
        user_id: int,
        token_address: str,
        chain: str,
        token_name: str = "",
        token_symbol: str = "",
        min_amount: float = 0.0,
    ) -> bool:
        """Add a token to track. Returns True if newly added."""
        key = self._key(chat_id, token_address)
        if key in self._data["tracked"]:
            return False

        self._data["tracked"][key] = {
            "chat_id": chat_id,
            "user_id": user_id,
            "token_address": token_address.lower(),
            "chain": chain.lower(),
            "token_name": token_name,
            "token_symbol": token_symbol,
            "min_amount": min_amount,
            "added_at": time.time(),
            "last_checked": 0,
            "last_tx_hash": "",
        }
        self._save()
        return True

    def remove_token(self, chat_id: int, token_address: str) -> bool:
        """Remove a tracked token. Returns True if it existed."""
        key = self._key(chat_id, token_address)
        if key in self._data["tracked"]:
            del self._data["tracked"][key]
            self._save()
            return True
        return False

    def get_tracked(self, chat_id: int) -> list[dict]:
        """Get all tracked tokens for a specific chat."""
        return [v for k, v in self._data["tracked"].items() if v["chat_id"] == chat_id]

    def get_all_tracked(self) -> list[dict]:
        """Get all tracked tokens across all chats."""
        return list(self._data["tracked"].values())

    def get_unique_tokens(self) -> list[dict]:
        """Get unique token addresses (for efficient scanning)."""
        seen = {}
        for entry in self._data["tracked"].values():
            addr = entry["token_address"]
            chain = entry["chain"]
            combo = f"{chain}:{addr}"
            if combo not in seen:
                seen[combo] = entry
        return list(seen.values())

    def get_chats_for_token(self, token_address: str, chain: str) -> list[dict]:
        """Get all chats tracking a specific token on a chain."""
        addr = token_address.lower()
        return [
            v
            for v in self._data["tracked"].values()
            if v["token_address"] == addr and v["chain"] == chain.lower()
        ]

    def update_last_checked(self, token_address: str, chain: str, tx_hash: str = ""):
        """Update the last checked timestamp for a token."""
        addr = token_address.lower()
        for v in self._data["tracked"].values():
            if v["token_address"] == addr and v["chain"] == chain.lower():
                v["last_checked"] = time.time()
                if tx_hash:
                    v["last_tx_hash"] = tx_hash
        self._save()

    def is_tracked(self, chat_id: int, token_address: str) -> bool:
        return self._key(chat_id, token_address) in self._data["tracked"]
