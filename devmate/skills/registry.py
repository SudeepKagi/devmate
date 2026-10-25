from __future__ import annotations

import re
from pathlib import Path
from devmate.observability.logger import get_logger

logger = get_logger(__name__)

SKILL_FILENAME = "SKILL.md"


class SkillNotFoundError(Exception):
    pass


class SkillRegistry:
    """Owns the in-memory catalog of all skills found in skills_dir.

    Expected layout on disk:
    skills_dir/
      python_debug/
        SKILL.md       <- required frontmatter + instructions
        scripts/       <- optional
        templates/     <- optional
        resources/     <- optional
    """

    def __init__(self, skills_dir: Path) -> None:
        self._skills_dir = Path(skills_dir)
        self._skills: dict[str, dict] = {}

    def load(self) -> None:
        """Walk skills_dir and parse every SKILL.md found."""
        self._skills.clear()
        if not self._skills_dir.exists():
            logger.warning(f"skills_dir not found: {self._skills_dir}. No skills loaded.")
            return

        for skill_dir in self._skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_file = skill_dir / SKILL_FILENAME
            if not skill_file.exists():
                logger.warning(f"Skipping {skill_dir.name}: no SKILL.md found")
                continue

            try:
                meta, body = _parse_skill_file(skill_file)
                name = meta.get("name", skill_dir.name)
                self._skills[name] = {
                    "meta": meta,
                    "body": body,
                    "skill_dir": skill_dir,
                }
                logger.info(f"Loaded skill: {name}")
            except Exception as e:
                logger.error(f"Failed to load skill from {skill_dir.name}: {e}")

    def build_skills_prompt(self) -> str:
        """Returns a compact string appended to the agent's SYSTEM_PROMPT at startup.
        ONLY includes metadata (name, description, when_to_use) — NOT the full skill body.
        """
        if not self._skills:
            return ""

        lines = ["=== Available Skills ==="]
        for name, skill in self._skills.items():
            meta = skill["meta"]
            description = meta.get("description", "No description provided.")
            when_to_use = meta.get("when_to_use", "")
            line = f"- {name}: {description}"
            if when_to_use:
                line += f" | when_to_use: {when_to_use}"
            lines.append(line)

        lines.append(
            "\nWhen the user's request matches a skill, call load_skill(name) "
            "to get the full instructions before proceeding."
        )
        return "\n".join(lines)

    def load_skill(self, name: str) -> str:
        """Returns the full SKILL.md body for the named skill, plus a listing of
        any support files inside the skill's folder.
        """
        if name not in self._skills:
            available = ", ".join(self._skills.keys()) or "none"
            raise SkillNotFoundError(
                f"Skill '{name}' not found. Available skills: {available}"
            )

        skill = self._skills[name]
        body = skill["body"]
        skill_dir: Path = skill["skill_dir"]

        support_files = _list_support_files(skill_dir)
        result = body
        if support_files:
            result += "\n\n--- Support Files Available ---\n"
            result += "\n".join(f"  {p}" for p in support_files)
            result += (
                "\nYou can read any of these files using the read_file tool "
                "if the skill instructions reference them."
            )
        return result

    @property
    def skill_names(self) -> list[str]:
        return list(self._skills.keys())


def _parse_skill_file(path: Path) -> tuple[dict, str]:
    """Read a SKILL.md and split it into (frontmatter_dict, body_str)."""
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
    if not match:
        return {}, text.strip()

    frontmatter_str = match.group(1)
    body = match.group(2).strip()
    meta = _parse_yaml(frontmatter_str)
    return meta, body


def _parse_yaml(text: str) -> dict:
    """Parse frontmatter YAML string into a dict."""
    try:
        import yaml
        return yaml.safe_load(text) or {}
    except ImportError:
        pass

    result = {}
    for line in text.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


def _list_support_files(skill_dir: Path) -> list[str]:
    """Return the absolute paths of every file inside the skill folder except SKILL.md."""
    files = []
    for f in skill_dir.rglob("*"):
        if f.is_file() and f.name != SKILL_FILENAME:
            files.append(str(f.resolve()))
    return files
