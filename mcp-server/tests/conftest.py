from __future__ import annotations

from pathlib import Path

import pytest


def _write_skill(skills_dir: Path, name: str, *, internal: bool = False, required_env: list[dict] | None = None,
                  with_script: bool = False, body: str = "Do the thing.\n") -> None:
    skill_dir = skills_dir / name
    skill_dir.mkdir(parents=True)

    frontmatter_lines = [
        "---",
        f"name: {name}",
        f"description: Test skill {name}.",
        "version: 1.0.0",
    ]
    if internal or required_env:
        frontmatter_lines.append("metadata:")
        if internal:
            frontmatter_lines.append("  internal: true")
    if required_env:
        frontmatter_lines.append("required_environment_variables:")
        for var in required_env:
            frontmatter_lines.append(f"  - name: {var['name']}")
            frontmatter_lines.append(f"    required_for: {var['required_for']}")
    frontmatter_lines.append("---")

    (skill_dir / "SKILL.md").write_text("\n".join(frontmatter_lines) + "\n\n" + body, encoding="utf-8")

    if with_script:
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / f"{name}_tool.py").write_text(
            "import argparse\n\n"
            "def build_parser():\n"
            "    p = argparse.ArgumentParser()\n"
            "    sub = p.add_subparsers(dest='tool', required=True)\n"
            "    sub.add_parser('now', help='Current time')\n"
            "    return p\n",
            encoding="utf-8",
        )


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """A synthetic skills/ tree matching real frontmatter shapes, so
    registry tests don't depend on the live repo staying exactly as-is.
    """
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    _write_skill(skills_dir, "jira", with_script=True, required_env=[
        {"name": "JIRA_BASE_URL", "required_for": "all functionality"},
        {"name": "JIRA_DEFAULT_PROJECT", "required_for": "optional -- scopes issue lookups"},
    ])
    _write_skill(skills_dir, "jira-worklog", body="Log time against an issue.\n")
    _write_skill(skills_dir, "mood")
    _write_skill(skills_dir, "telegram", internal=True, with_script=True, required_env=[
        {"name": "TELEGRAM_API_ID", "required_for": "all functionality"},
    ])
    return tmp_path
