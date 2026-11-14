"""Tests for scripts/sync_shared.py.

Run from the repo root: `pytest -q scripts/tests`.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

spec = importlib.util.spec_from_file_location(
    "sync_shared", REPO_ROOT / "scripts" / "sync_shared.py"
)
sync_shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync_shared)


def _tree(root: Path) -> Path:
    skills = root / "skills"
    for source in sync_shared.CONSUMERS:
        path = skills / "_shared" / source
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {source}\n")
    return skills


def test_real_repo_copies_match_shared_sources():
    assert sync_shared.check() == []


def test_real_repo_copies_are_regular_files():
    # npx skills skips symlinks that point outside the skill directory.
    for _, copy in sync_shared.pairs():
        assert not copy.is_symlink(), copy


def test_check_reports_missing_symlinked_and_stale_copies(tmp_path):
    skills = _tree(tmp_path)
    pairs = sync_shared.pairs(skills)
    (source0, copy0), (source1, copy1) = pairs[0], pairs[1]
    copy0.parent.mkdir(parents=True, exist_ok=True)
    copy0.symlink_to(source0)
    copy1.parent.mkdir(parents=True, exist_ok=True)
    copy1.write_text("stale\n")

    errors = sync_shared.check(skills)

    assert len(errors) == len(pairs)
    assert any("symlink" in e for e in errors)
    assert any("differs" in e for e in errors)
    assert any("missing" in e for e in errors)


def test_sync_replaces_symlinks_and_stale_copies_and_is_idempotent(tmp_path):
    skills = _tree(tmp_path)
    source, copy = sync_shared.pairs(skills)[0]
    copy.parent.mkdir(parents=True, exist_ok=True)
    copy.symlink_to(source)

    changed = sync_shared.sync(skills)

    assert len(changed) == len(sync_shared.pairs(skills))
    assert not copy.is_symlink()
    assert copy.read_bytes() == source.read_bytes()
    assert sync_shared.check(skills) == []
    assert sync_shared.sync(skills) == []
