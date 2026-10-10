#!/usr/bin/env python3
"""Install the Python dependencies of every installed skill that has any.

`npx skills add` copies a skill's files but never installs its
dependencies. A toolset's CLI already runs without a separate install
step under `uv run` (each `scripts/*.py` entry point declares its own
dependencies inline, PEP 723), so this script is for the other path: an
environment without `uv`, where the CLI runs as `python3 scripts/...` and
its dependencies must already be importable by that interpreter.

Discovery: every skill directory `npx skills ls --json` reports (global
scope plus the current directory's project scope), or the directories
given with `--skills-dir`, keeping only those with a `requirements.txt`
next to their `SKILL.md`. Every requirements file found is installed in
one resolver run into `--python`'s environment, with that interpreter's
own pip (or `uv pip` when it has no pip).

Driven by the top-level Makefile (`make install-skill-deps`); stdlib only,
so it runs before any dependency is installed.

Usage:
    scripts/install_skill_deps.py [--python python3] [--skills-dir DIR ...]
        [--dry-run] [-- <extra pip install args>]
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REQUIREMENTS = "requirements.txt"


def npx_skill_dirs(cwd: Path) -> list[Path]:
    """Return every installed skill directory `npx skills ls` knows about."""
    npx = shutil.which("npx")
    if npx is None:
        raise SystemExit(
            "error: `npx` not found, so installed skills can't be listed.\n"
            "Pass the directory your agent loads skills from instead, e.g.\n"
            "  make install-skill-deps SKILLS_DIR=~/.claude/skills"
        )
    dirs: list[Path] = []
    for scope_args in (["-g"], []):
        proc = subprocess.run(
            [npx, "--yes", "skills", "ls", "--json", *scope_args],
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise SystemExit(
                f"error: `npx skills ls --json {' '.join(scope_args)}` failed:\n"
                f"{proc.stderr.strip()}"
            )
        try:
            entries = json.loads(proc.stdout or "[]")
        except json.JSONDecodeError:
            raise SystemExit(
                f"error: `npx skills ls --json` printed non-JSON output:\n{proc.stdout[:500]}"
            )
        dirs.extend(Path(e["path"]) for e in entries if e.get("path"))
    return dirs


def skills_in(root: Path) -> list[Path]:
    """Return `root` itself if it is a skill, else its immediate skill subdirectories."""
    if (root / "SKILL.md").is_file():
        return [root]
    if not root.is_dir():
        raise SystemExit(f"error: skills directory not found: {root}")
    return sorted(p for p in root.iterdir() if (p / "SKILL.md").is_file())


def find_requirements(skill_dirs: list[Path]) -> list[Path]:
    """Return each distinct skill's requirements file, deduplicated by real path.

    The same skill is often reachable through several agent directories
    (symlinks into one canonical copy), so dedupe on the resolved file.
    """
    seen: dict[Path, Path] = {}
    for skill_dir in skill_dirs:
        req = skill_dir / REQUIREMENTS
        if req.is_file():
            seen.setdefault(req.resolve(), req)
    return sorted(seen.values(), key=lambda p: p.parent.name)


def install_command(python: str, requirements: list[Path], extra: list[str]) -> list[str]:
    """Build the one install command for every requirements file."""
    req_args = [arg for req in requirements for arg in ("-r", str(req))]
    has_pip = subprocess.run(
        [python, "-m", "pip", "--version"], capture_output=True
    ).returncode == 0
    if has_pip:
        return [python, "-m", "pip", "install", *req_args, *extra]
    uv = shutil.which("uv")
    if uv is not None:
        return [uv, "pip", "install", "--python", python, *req_args, *extra]
    raise SystemExit(
        f"error: `{python}` has no pip and `uv` isn't installed.\n"
        f"Install pip for it (e.g. `{python} -m ensurepip --user`), or pass\n"
        "PYTHON=/path/to/a/venv/bin/python."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="install_skill_deps",
        description="Install the Python dependencies of every installed skill.",
    )
    parser.add_argument(
        "--python",
        default="python3",
        help="Interpreter whose environment receives the dependencies "
        "(the one your agent runs `python3 scripts/...` with).",
    )
    parser.add_argument(
        "--skills-dir",
        action="append",
        default=[],
        help="A skills directory (or a single skill) to scan instead of asking "
        "`npx skills ls`. Repeatable.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be installed and the install command, then stop.",
    )
    parser.add_argument(
        "pip_args",
        nargs="*",
        help="Extra arguments passed to the install command (after `--`).",
    )
    args = parser.parse_args(argv)

    if args.skills_dir:
        skill_dirs = [d for root in args.skills_dir for d in skills_in(Path(root).expanduser())]
    else:
        skill_dirs = npx_skill_dirs(Path.cwd())

    requirements = find_requirements(skill_dirs)
    if not requirements:
        print("No installed skill has Python dependencies; nothing to do.")
        return 0

    print("Installing Python dependencies for:")
    for req in requirements:
        print(f"  {req.parent.name:<12} {req}")

    if args.dry_run:
        req_args = " ".join(f"-r {req}" for req in requirements)
        print(f"\n(dry run) would run: {args.python} -m pip install {req_args} "
              f"{' '.join(args.pip_args)}".rstrip())
        return 0

    cmd = install_command(args.python, requirements, args.pip_args)
    print(f"\n$ {' '.join(cmd)}", flush=True)
    code = subprocess.run(cmd).returncode
    if code != 0:
        print(
            "\nInstall failed. If pip refused with \"externally-managed-environment\",\n"
            "point PYTHON at a virtualenv's interpreter (the same one your agent\n"
            "runs the skills with), e.g.:\n"
            "  make install-skill-deps PYTHON=/path/to/venv/bin/python",
            file=sys.stderr,
        )
    return code


if __name__ == "__main__":
    sys.exit(main())
