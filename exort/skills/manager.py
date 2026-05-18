"""
Skills manager — loads and manages markdown-based skill files.

Skills are markdown files that contain specialized knowledge, workflows,
and instructions for specific tasks. They're injected into the agent's
context when relevant.

Usage:
    manager = SkillsManager()
    manager.load_all()
    context = manager.get_context_for("python web scraping")
"""

import os
from pathlib import Path
from typing import Optional


class Skill:
    """A loaded skill file."""

    def __init__(self, name: str, path: str, content: str, category: str = ""):
        self.name = name
        self.path = path
        self.content = content
        self.category = category

    def __repr__(self):
        return f"Skill({self.name}, category={self.category})"


class SkillsManager:
    """
    Manages markdown skill files.

    Skills are loaded from:
    - ~/.exort/skills/ (user skills)
    - exort/skills/builtin/ (built-in skills)
    """

    def __init__(self, skills_dir: Optional[str] = None):
        from exort.config import get_exort_home
        self._user_dir = Path(skills_dir) if skills_dir else get_exort_home() / "skills"
        self._builtin_dir = Path(__file__).parent / "builtin"
        self._skills: dict[str, Skill] = {}

    def load_all(self):
        """Load all skills from user and builtin directories."""
        self._skills.clear()
        self._load_dir(self._user_dir, category="user")
        self._load_dir(self._builtin_dir, category="builtin")

    def _load_dir(self, directory: Path, category: str):
        """Load all .md files from a directory as skills."""
        if not directory.exists():
            return
        for md_file in directory.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                name = md_file.stem.lower().replace(" ", "-")
                self._skills[name] = Skill(
                    name=name,
                    path=str(md_file),
                    content=content,
                    category=category,
                )
            except Exception:
                continue

    def get_skill(self, name: str) -> Optional[Skill]:
        """Get a skill by name."""
        return self._skills.get(name.lower())

    def list_skills(self) -> list[dict]:
        """List all loaded skills."""
        return [
            {"name": s.name, "path": s.path, "category": s.category}
            for s in self._skills.values()
        ]

    def search(self, query: str) -> list[Skill]:
        """Search skills by keyword relevance."""
        query_lower = query.lower()
        results = []
        for skill in self._skills.values():
            # Simple keyword matching
            score = 0
            if query_lower in skill.name:
                score += 3
            if query_lower in skill.content.lower():
                score += 1
            if score > 0:
                results.append((score, skill))
        results.sort(key=lambda x: x[0], reverse=True)
        return [skill for _, skill in results[:3]]

    def get_context_for(self, query: str, max_chars: int = 3000) -> str:
        """Get relevant skill context for a query."""
        relevant = self.search(query)
        if not relevant:
            return ""
        parts = []
        for skill in relevant:
            content = skill.content[:max_chars]
            parts.append(f"--- Skill: {skill.name} ---\n{content}")
        return "\n\n".join(parts)

    def create_skill(self, name: str, content: str) -> str:
        """Create a new user skill."""
        self._user_dir.mkdir(parents=True, exist_ok=True)
        path = self._user_dir / f"{name}.md"
        path.write_text(content, encoding="utf-8")
        self._skills[name] = Skill(name=name, path=str(path), content=content, category="user")
        return str(path)

    def __len__(self):
        return len(self._skills)

    def __repr__(self):
        return f"SkillsManager({len(self._skills)} skills)"
