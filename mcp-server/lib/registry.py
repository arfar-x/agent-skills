"""Find, parse, and classify every skills/*/SKILL.md in the repo.

`SKILL.md` stays the source of truth for instructions -- this module
only reads and classifies, it never rewrites or duplicates a skill's
content beyond what's needed to build a listing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from .introspect import SubcommandSpec, introspect_subcommands, load_build_parser

SkillKind = Literal["standalone", "toolset_root", "toolset_thin_wrapper"]


@dataclass(frozen=True)
class SkillManifest:
    name: str  # frontmatter `name`, e.g. "jira", "jira-worklog"
    dir_path: Path
    skill_md_path: Path
    kind: SkillKind
    internal: bool
    required_environment_variables: tuple[dict, ...]
    frontmatter: dict
    body: str  # markdown body, as read at discovery time (get_skill re-reads live)
    script_path: Path | None = None  # set only for toolset_root
    toolset: str | None = None  # e.g. "jira" -- set for toolset_root and toolset_thin_wrapper


def parse_skill_md(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"{path}: no YAML frontmatter delimiter.")
    _, fm_text, body = text.split("---", 2)
    frontmatter = yaml.safe_load(fm_text) or {}
    return frontmatter, body.lstrip("\n")


def _is_internal(frontmatter: dict) -> bool:
    return bool((frontmatter.get("metadata") or {}).get("internal", False))


def discover_skills(repo_root: Path, *, include_internal: bool) -> list[SkillManifest]:
    """Scan skills/*/SKILL.md, classify each, and apply internal-skill
    gating. `include_internal` is the caller's already-resolved decision
    (server.py's --include-internal flag, falling back to
    INSTALL_INTERNAL_SKILLS=1) -- this function doesn't read the env
    itself, so it stays trivially testable.
    """
    skills_dir = repo_root / "skills"

    candidates: dict[str, Path] = {}
    for entry in sorted(skills_dir.iterdir()):
        skill_md = entry / "SKILL.md"
        if entry.is_dir() and skill_md.exists():
            candidates[entry.name] = skill_md

    toolset_roots = {
        name for name in candidates if (skills_dir / name / "scripts" / f"{name}_tool.py").exists()
    }

    manifests: list[SkillManifest] = []
    for name, skill_md_path in candidates.items():
        frontmatter, body = parse_skill_md(skill_md_path)
        internal = _is_internal(frontmatter)
        if internal and not include_internal:
            continue

        required_env = tuple(frontmatter.get("required_environment_variables", []))
        dir_path = skills_dir / name

        if name in toolset_roots:
            manifests.append(
                SkillManifest(
                    name=name, dir_path=dir_path, skill_md_path=skill_md_path,
                    kind="toolset_root", internal=internal,
                    required_environment_variables=required_env, frontmatter=frontmatter, body=body,
                    script_path=dir_path / "scripts" / f"{name}_tool.py", toolset=name,
                )
            )
            continue

        # Longest-prefix match against known toolset roots, e.g. "jira-worklog-report"
        # matches root "jira". Sorted by descending root-name length so this stays
        # deterministic if roots ever nest (e.g. hypothetical "jira" and "jira-cloud").
        matched_root = next(
            (root for root in sorted(toolset_roots, key=len, reverse=True) if name.startswith(f"{root}-")),
            None,
        )
        if matched_root:
            manifests.append(
                SkillManifest(
                    name=name, dir_path=dir_path, skill_md_path=skill_md_path,
                    kind="toolset_thin_wrapper", internal=internal,
                    required_environment_variables=required_env, frontmatter=frontmatter, body=body,
                    toolset=matched_root,
                )
            )
        else:
            manifests.append(
                SkillManifest(
                    name=name, dir_path=dir_path, skill_md_path=skill_md_path,
                    kind="standalone", internal=internal,
                    required_environment_variables=required_env, frontmatter=frontmatter, body=body,
                )
            )
    return manifests


def load_subcommands(manifest: SkillManifest) -> list[SubcommandSpec]:
    """Only valid for kind == 'toolset_root'. Raises IntrospectionError,
    which the caller (server.py's startup loop) catches per-toolset so one
    broken toolset doesn't prevent every other toolset's tools/get_skill
    from registering.
    """
    assert manifest.kind == "toolset_root" and manifest.script_path is not None
    build_parser = load_build_parser(manifest.script_path)
    return introspect_subcommands(build_parser())


def resolve_include_internal(cli_flag: bool) -> bool:
    """--include-internal (explicit at launch) wins; otherwise fall back
    to this repo's existing INSTALL_INTERNAL_SKILLS=1 convention so the
    two mechanisms agree instead of diverging.
    """
    if cli_flag:
        return True
    return os.environ.get("INSTALL_INTERNAL_SKILLS") == "1"
