"""Tests for scripts/install_skill_deps.py and the inline (PEP 723)
dependency blocks it complements.

Run from the repo root: `pytest -q scripts/tests`.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS = REPO_ROOT / "skills"

spec = importlib.util.spec_from_file_location(
    "install_skill_deps", REPO_ROOT / "scripts" / "install_skill_deps.py"
)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


def _skill(root: Path, name: str, requirements: str | None = None) -> Path:
    d = root / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(f"---\nname: {name}\n---\n")
    if requirements is not None:
        (d / "requirements.txt").write_text(requirements)
    return d


def test_find_requirements_keeps_only_skills_with_requirements(tmp_path):
    a = _skill(tmp_path, "alpha", "requests\n")
    b = _skill(tmp_path, "beta")
    assert installer.find_requirements([a, b]) == [a / "requirements.txt"]


def test_find_requirements_dedupes_symlinked_copies(tmp_path):
    real = _skill(tmp_path / "canonical", "alpha", "requests\n")
    (tmp_path / "agent").mkdir()
    link = tmp_path / "agent" / "alpha"
    link.symlink_to(real)
    assert len(installer.find_requirements([real, link])) == 1


def test_skills_in_accepts_a_skills_dir_or_a_single_skill(tmp_path):
    a = _skill(tmp_path, "alpha")
    b = _skill(tmp_path, "beta")
    (tmp_path / "not-a-skill").mkdir()
    assert installer.skills_in(tmp_path) == [a, b]
    assert installer.skills_in(a) == [a]


def test_install_command_uses_the_interpreters_own_pip(tmp_path):
    req = tmp_path / "requirements.txt"
    cmd = installer.install_command(sys.executable, [req], ["--user"])
    assert cmd == [sys.executable, "-m", "pip", "install", "-r", str(req), "--user"]


def test_dry_run_installs_nothing(tmp_path, capsys, monkeypatch):
    _skill(tmp_path, "alpha", "requests\n")
    monkeypatch.setattr(installer.subprocess, "run", lambda *a, **k: pytest.fail("ran a command"))
    assert installer.main(["--skills-dir", str(tmp_path), "--dry-run"]) == 0
    assert "alpha" in capsys.readouterr().out


TOOLSET_SCRIPTS = sorted(
    p
    for p in SKILLS.glob("*/scripts/*.py")
    if (p.parents[1] / "requirements.txt").is_file() and "# /// script" in p.read_text()
)


def _inline_dependencies(script: Path) -> list[str]:
    block = re.search(r"^# /// script\n(.*?)^# ///$", script.read_text(), re.S | re.M)
    assert block, f"{script} has no PEP 723 block"
    return re.findall(r'^#\s+"([^"]+)",?$', block.group(1), re.M)


def _requirements(toolset: Path) -> list[str]:
    lines = (toolset / "requirements.txt").read_text().splitlines()
    return [l.strip() for l in lines if l.strip() and not l.lstrip().startswith("#")]


def test_every_toolset_with_requirements_declares_them_inline():
    for req in SKILLS.glob("*/requirements.txt"):
        dispatcher = req.parent / "scripts" / f"{req.parent.name}_tool.py"
        assert dispatcher in TOOLSET_SCRIPTS, f"{dispatcher} lacks a PEP 723 block"


@pytest.mark.parametrize("script", TOOLSET_SCRIPTS, ids=lambda p: str(p.relative_to(SKILLS)))
def test_inline_dependencies_match_requirements_txt(script):
    # `uv run` reads the inline block, `pip install -r` reads requirements.txt;
    # they must not drift apart.
    assert sorted(_inline_dependencies(script)) == sorted(_requirements(script.parents[1]))
