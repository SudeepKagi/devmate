from __future__ import annotations

from pathlib import Path
from langchain_core.tools import tool
from devmate.config import config
from devmate.skills.registry import SkillRegistry, SkillNotFoundError
from devmate.observability.logger import get_logger

logger = get_logger(__name__)

_registry: SkillRegistry | None = None


def get_registry() -> SkillRegistry:
    """Return the process-wide SkillRegistry, building it on first call."""
    global _registry
    if _registry is None:
        configured_dir = config.get("skills", {}).get("skills_dir", ".devmate/skills")
        skills_dir = Path.cwd() / configured_dir
        if not skills_dir.exists():
            # Check fallback to .educosys/skills
            alt_dir = Path.cwd() / ".educosys/skills"
            if alt_dir.exists():
                skills_dir = alt_dir
        _registry = SkillRegistry(skills_dir)
        _registry.load()
        logger.info(f"SkillRegistry initialized from: {skills_dir}")
    return _registry


def build_skills_prompt() -> str:
    """Trigger registry initialization and return the metadata-only prompt snippet."""
    return get_registry().build_skills_prompt()


@tool
def load_skill(name: str) -> str:
    """Load the full instructions for a skill by name.
    Call this when the user's request matches one of the skills listed in your system prompt.
    Returns the skill's step-by-step instructions and lists any available support files
    (scripts, templates, resources) that you can read using the read_file tool.
    """
    logger.info(f"Tool called: load_skill('{name}')")
    try:
        return get_registry().load_skill(name)
    except SkillNotFoundError as e:
        return str(e)
