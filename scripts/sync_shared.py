#!/usr/bin/env python3
"""Keep each toolset's copies of `skills/_shared/` files in sync.

`npx skills add` copies a skill's own directory only and skips any
symlink that resolves outside it, so a toolset cannot symlink into
`skills/_shared/`: the installed skill would be missing those files.
Each toolset therefore carries a real, byte-identical copy in its own
`lib/`, and `skills/_shared/` stays the single source of truth.

    scripts/sync_shared.py           # rewrite every copy from its source
    scripts/sync_shared.py --check   # exit 1 if any copy is missing,
                                     # a symlink, or differs from its source

Stdlib only. Edit the file under `skills/_shared/`, then run this.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS = REPO_ROOT / "skills"

# shared source (relative to skills/_shared) -> consumers (relative to skills/)
CONSUMERS: dict[str, list[str]] = {
    "credentials/http.py": [
        "jira/lib/credentials.py",
        "confluence/lib/credentials.py",
        "glab/lib/credentials.py",
    ],
    "attachments/files.py": [
        "jira/lib/attachment_files.py",
        "confluence/lib/attachment_files.py",
    ],
    "text/patch.py": [
        "jira/lib/text_patch.py",
        "confluence/lib/text_patch.py",
    ],
}


def pairs(skills: Path = SKILLS) -> list[tuple[Path, Path]]:
    return [
        (skills / "_shared" / source, skills / consumer)
        for source, consumers in CONSUMERS.items()
        for consumer in consumers
    ]


def problem(source: Path, copy: Path) -> str | None:
    """Why `copy` is not a faithful copy of `source`, or None if it is."""
    if copy.is_symlink():
        return "is a symlink (npx skills drops symlinks that leave the skill)"
    if not copy.exists():
        return "is missing"
    if copy.read_bytes() != source.read_bytes():
        return "differs from its source"
    return None


def check(skills: Path = SKILLS) -> list[str]:
    errors = []
    for source, copy in pairs(skills):
        reason = problem(source, copy)
        if reason:
            errors.append(f"{copy.relative_to(skills)} {reason}: {source.relative_to(skills)}")
    return errors


def sync(skills: Path = SKILLS) -> list[Path]:
    changed = []
    for source, copy in pairs(skills):
        if problem(source, copy) is None:
            continue
        if copy.is_symlink() or copy.exists():
            copy.unlink()
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, copy)
        changed.append(copy)
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="report drift, change nothing")
    args = parser.parse_args(argv)

    if args.check:
        errors = check()
        for line in errors:
            print(line, file=sys.stderr)
        if errors:
            print("run scripts/sync_shared.py to fix", file=sys.stderr)
        return 1 if errors else 0

    for path in sync():
        print(f"synced {path.relative_to(SKILLS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
