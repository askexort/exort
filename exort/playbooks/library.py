"""
PlaybookLibrary — load and query knowledge files.

A "playbook" is a markdown file containing specialized instructions,
workflows, or domain knowledge.  The engine can pull relevant playbooks
into its context when the user's request matches.

Playbooks live in:
  ~/.exort/playbooks/     (user-created)
  exort/playbooks/builtin/ (shipped with Exort)
"""

import os
from pathlib import Path
from typing import Optional


class Playbook:
    __slots__ = ("name", "path", "body", "origin")

    def __init__(self, name: str, path: str, body: str, origin: str = "user"):
        self.name = name
        self.path = path
        self.body = body
        self.origin = origin

    def __repr__(self):
        return f"Playbook({self.name}, {self.origin})"


class PlaybookLibrary:
    """
    Loads .md playbooks and searches them by keyword.

        lib = PlaybookLibrary()
        lib.load()
        ctx = lib.context_for("web scraping")   # relevant playbook text
    """

    def __init__(self, user_dir: Optional[str] = None):
        from exort.config import exort_dir
        self._user = Path(user_dir) if user_dir else exort_dir() / "playbooks"
        self._builtin = Path(__file__).parent / "builtin"
        self._books: dict[str, Playbook] = {}

    def load(self):
        """Load all playbooks from disk."""
        self._books.clear()
        self._scan(self._user, "user")
        self._scan(self._builtin, "builtin")

    def _scan(self, directory: Path, origin: str):
        if not directory.exists():
            return
        for f in directory.rglob("*.md"):
            try:
                body = f.read_text(encoding="utf-8")
                name = f.stem.lower().replace(" ", "-")
                self._books[name] = Playbook(name, str(f), body, origin)
            except Exception:
                pass

    def find(self, query: str, max_results: int = 3) -> list[Playbook]:
        """Return playbooks matching a keyword query."""
        q = query.lower()
        scored = []
        for pb in self._books.values():
            score = 0
            if q in pb.name:
                score += 3
            if q in pb.body.lower():
                score += 1
            if score:
                scored.append((score, pb))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [pb for _, pb in scored[:max_results]]

    def context_for(self, query: str, max_chars: int = 3000) -> str:
        """Get relevant playbook text for injection into the engine."""
        matches = self.find(query)
        if not matches:
            return ""
        parts = []
        for pb in matches:
            parts.append(f"--- Playbook: {pb.name} ---\n{pb.body[:max_chars]}")
        return "\n\n".join(parts)

    def save(self, name: str, body: str) -> str:
        """Create a new user playbook."""
        self._user.mkdir(parents=True, exist_ok=True)
        p = self._user / f"{name}.md"
        p.write_text(body, encoding="utf-8")
        self._books[name] = Playbook(name, str(p), body, "user")
        return str(p)

    def list_all(self) -> list[dict]:
        return [{"name": pb.name, "origin": pb.origin, "path": pb.path}
                for pb in self._books.values()]

    def __len__(self):
        return len(self._books)
