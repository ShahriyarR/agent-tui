"""Skill loader for agent-tui.

Provides filesystem-based skill discovery.  A "skill" is a directory that
contains a ``SKILL.md`` file.  The directory name is the skill name and the
first non-empty line of ``SKILL.md`` (after stripping YAML front-matter) is
used as the description.

This is a standalone implementation that does **not** depend on the deepagents
middleware stack.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

# Skill metadata is a plain dict so it can be passed across thread boundaries
# without pickling issues and compared easily in tests.
SkillMetadata = dict[str, Any]


class ExtendedSkillMetadata(dict):  # type: ignore[type-arg]
    """Extended skill metadata with source tracking.

    Keys:
        name: Normalised skill name (directory name, lowercase).
        description: Short description (first non-empty line of SKILL.md after
            stripping YAML front-matter, or empty string if not available).
        path: Absolute path to the SKILL.md file as a string.
        source: Origin of the skill — one of ``'built-in'``, ``'user'``,
            ``'project'``, or ``'claude (experimental)'``.
    """

    # Not a real dataclass — just a typed dict alias so isinstance checks work.


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_YAML_FRONT_MATTER_RE = re.compile(r"^---\s*\n.*?^---\s*\n", re.DOTALL | re.MULTILINE)


def _extract_description(content: str) -> str:
    """Extract first non-empty line from SKILL.md, skipping YAML front-matter.

    Args:
        content: Full text of the SKILL.md file.

    Returns:
        First non-empty text line, or empty string.
    """
    body = _YAML_FRONT_MATTER_RE.sub("", content, count=1).lstrip()
    for line in body.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            return stripped
    return ""


def _load_skills_from_dir(
    skill_dir: Path,
    source_label: Literal["built-in", "user", "project", "claude (experimental)"],
) -> list[ExtendedSkillMetadata]:
    """Scan *skill_dir* for SKILL.md files and return metadata for each.

    Args:
        skill_dir: Directory to scan.  Each immediate subdirectory that
            contains a ``SKILL.md`` file is treated as a skill.
        source_label: Label to attach to every skill found here.

    Returns:
        List of :class:`ExtendedSkillMetadata` dicts, one per skill.
    """
    skills: list[ExtendedSkillMetadata] = []
    try:
        for entry in sorted(skill_dir.iterdir()):
            if not entry.is_dir():
                continue
            skill_md = entry / "SKILL.md"
            if not skill_md.is_file():
                continue
            try:
                content = skill_md.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                logger.warning(
                    "Could not read SKILL.md at %s", skill_md, exc_info=True
                )
                continue
            meta: ExtendedSkillMetadata = ExtendedSkillMetadata(
                {
                    "name": entry.name.lower(),
                    "description": _extract_description(content),
                    "path": str(skill_md),
                    "source": source_label,
                }
            )
            skills.append(meta)
    except OSError:
        logger.warning(
            "Could not scan skill directory %s", skill_dir, exc_info=True
        )
    return skills


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def list_skills(
    *,
    built_in_skills_dir: Path | None = None,
    user_skills_dir: Path | None = None,
    project_skills_dir: Path | None = None,
    user_agent_skills_dir: Path | None = None,
    project_agent_skills_dir: Path | None = None,
    user_claude_skills_dir: Path | None = None,
    project_claude_skills_dir: Path | None = None,
) -> list[ExtendedSkillMetadata]:
    """List skills from built-in, user, and/or project directories.

    Precedence order (lowest to highest):
    0. ``built_in_skills_dir``
    1. ``user_skills_dir``
    2. ``user_agent_skills_dir``
    3. ``project_skills_dir``
    4. ``project_agent_skills_dir``
    5. ``user_claude_skills_dir``
    6. ``project_claude_skills_dir``

    Higher-precedence directories override skills with the same name.

    Args:
        built_in_skills_dir: Path to built-in skills shipped with the package.
        user_skills_dir: Path to ``~/.agent-tui/{agent}/skills/``.
        project_skills_dir: Path to ``.agent-tui/skills/``.
        user_agent_skills_dir: Path to ``~/.agents/skills/`` (alias).
        project_agent_skills_dir: Path to ``.agents/skills/`` (alias).
        user_claude_skills_dir: Path to ``~/.claude/skills/`` (experimental).
        project_claude_skills_dir: Path to ``.claude/skills/`` (experimental).

    Returns:
        Merged list of skill metadata, higher-precedence entries win on name
        conflicts.
    """
    sources: list[
        tuple[Path | None, Literal["built-in", "user", "project", "claude (experimental)"]]
    ] = [
        (built_in_skills_dir, "built-in"),
        (user_skills_dir, "user"),
        (user_agent_skills_dir, "user"),
        (project_skills_dir, "project"),
        (project_agent_skills_dir, "project"),
        (user_claude_skills_dir, "claude (experimental)"),
        (project_claude_skills_dir, "claude (experimental)"),
    ]

    all_skills: dict[str, ExtendedSkillMetadata] = {}
    for skill_dir, source_label in sources:
        if skill_dir is None or not skill_dir.exists():
            continue
        for skill in _load_skills_from_dir(skill_dir, source_label):
            all_skills[skill["name"]] = skill

    return list(all_skills.values())


def load_skill_content(
    skill_path: str,
    *,
    allowed_roots: "Sequence[Path]" = (),
) -> str | None:
    """Read the full raw SKILL.md content for a skill.

    When ``allowed_roots`` is provided, the resolved path must fall within at
    least one root directory to prevent symlink traversal attacks.

    Args:
        skill_path: Path to the SKILL.md file (from ``SkillMetadata['path']``).
        allowed_roots: Pre-resolved skill root directories.  If empty,
            containment is not checked.

    Returns:
        Full text content of the SKILL.md file, or ``None`` on read failure.

    Raises:
        PermissionError: If the resolved path is outside all ``allowed_roots``.
    """
    path = Path(skill_path).resolve()

    if allowed_roots and not any(path.is_relative_to(root) for root in allowed_roots):
        logger.warning(
            "Skill path %s is outside all allowed roots, refusing to read",
            skill_path,
        )
        from agent_tui.configurator.env_vars import EXTRA_SKILLS_DIRS

        msg = (
            f"Skill path {skill_path} resolves outside all allowed skill "
            "directories. If this is a symlink, add the target directory to "
            f"{EXTRA_SKILLS_DIRS} or [skills].extra_allowed_dirs "
            "in ~/.agent-tui/config.toml."
        )
        raise PermissionError(msg)

    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        logger.warning(
            "Could not read skill content from %s", skill_path, exc_info=True
        )
        return None
