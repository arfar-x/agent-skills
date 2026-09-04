from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from types import SimpleNamespace

from lib.doc_gen import build_doc_gen_tool, doc_type_manifests


def _manifest(name, kind, skill_md_path, doc_type=None):
    frontmatter = {"metadata": {"doc_type": doc_type}} if doc_type else {}
    return SimpleNamespace(name=name, kind=kind, skill_md_path=skill_md_path, frontmatter=frontmatter)


def _write_skill_md(path, doc_type):
    path.write_text(
        "---\n"
        f"name: {path.parent.name}\n"
        "description: test\n"
        "version: 1.0.0\n"
        "metadata:\n"
        f"  doc_type: {doc_type}\n"
        "---\n\n"
        f"Instructions for {doc_type}.\n",
        encoding="utf-8",
    )


def test_doc_type_manifests_only_includes_tagged_standalone_skills(tmp_path):
    prd_md = tmp_path / "prd_SKILL.md"
    prd_md.write_text("---\nname: prd\n---\n\nbody\n", encoding="utf-8")

    manifests = [
        _manifest("prd", "standalone", prd_md, doc_type="prd"),
        _manifest("mood", "standalone", prd_md, doc_type=None),
        _manifest("jira", "toolset_root", prd_md, doc_type="not_applicable"),
    ]
    result = doc_type_manifests(manifests)
    assert set(result) == {"prd"}


def test_build_doc_gen_tool_returns_none_when_no_doc_types(tmp_path):
    manifests = [_manifest("mood", "standalone", tmp_path / "x.md", doc_type=None)]
    assert build_doc_gen_tool(manifests) is None


def test_doc_gen_tool_enum_lists_available_doc_types(tmp_path):
    prd_path = tmp_path / "prd" / "SKILL.md"
    prd_path.parent.mkdir(parents=True)
    _write_skill_md(prd_path, "prd")

    trd_path = tmp_path / "trd" / "SKILL.md"
    trd_path.parent.mkdir(parents=True)
    _write_skill_md(trd_path, "trd")

    manifests = [
        _manifest("prd", "standalone", prd_path, doc_type="prd"),
        _manifest("trd", "standalone", trd_path, doc_type="trd"),
    ]
    tool = build_doc_gen_tool(manifests)
    assert tool.parameters["properties"]["doc_type"]["enum"] == ["prd", "trd"]
    assert tool.parameters["required"] == ["doc_type"]


def test_doc_gen_tool_returns_live_instructions_for_known_type(tmp_path):
    prd_path = tmp_path / "prd" / "SKILL.md"
    prd_path.parent.mkdir(parents=True)
    _write_skill_md(prd_path, "prd")

    manifests = [_manifest("prd", "standalone", prd_path, doc_type="prd")]
    tool = build_doc_gen_tool(manifests)

    result = asyncio.run(tool.run({"doc_type": "prd"}))
    text = result.content[0].text
    assert "Instructions for prd." in text
    assert '"skill_name":"prd"' in text.replace(" ", "")


def test_doc_gen_tool_includes_current_date_so_the_model_never_guesses(tmp_path):
    prd_path = tmp_path / "prd" / "SKILL.md"
    prd_path.parent.mkdir(parents=True)
    _write_skill_md(prd_path, "prd")

    manifests = [_manifest("prd", "standalone", prd_path, doc_type="prd")]
    tool = build_doc_gen_tool(manifests)

    result = asyncio.run(tool.run({"doc_type": "prd"}))
    payload = json.loads(result.content[0].text)

    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", payload["current_date"])
    assert payload["current_date"] == datetime.now(timezone.utc).date().isoformat()


def test_doc_gen_tool_missing_doc_type_returns_error_instead_of_raising(tmp_path):
    prd_path = tmp_path / "prd" / "SKILL.md"
    prd_path.parent.mkdir(parents=True)
    _write_skill_md(prd_path, "prd")

    manifests = [_manifest("prd", "standalone", prd_path, doc_type="prd")]
    tool = build_doc_gen_tool(manifests)

    result = asyncio.run(tool.run({}))
    text = result.content[0].text
    assert '"type":"missing_argument"' in text.replace(" ", "")
    assert '"available":["prd"]' in text.replace(" ", "")


def test_doc_gen_tool_unknown_type_lists_available_options(tmp_path):
    prd_path = tmp_path / "prd" / "SKILL.md"
    prd_path.parent.mkdir(parents=True)
    _write_skill_md(prd_path, "prd")

    manifests = [_manifest("prd", "standalone", prd_path, doc_type="prd")]
    tool = build_doc_gen_tool(manifests)

    result = asyncio.run(tool.run({"doc_type": "erd"}))
    text = result.content[0].text
    assert '"type":"not_found"' in text.replace(" ", "")
    assert '"available":["prd"]' in text.replace(" ", "")
