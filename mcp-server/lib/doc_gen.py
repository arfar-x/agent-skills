"""`doc_gen` -- a single MCP tool covering every "generate a document from
a template" standalone skill (prd, trd, and whatever's added later: erd,
adr, rfc, ...).

A document-generation skill opts in by setting `metadata.doc_type: <slug>`
in its own SKILL.md frontmatter -- see skills/prd/SKILL.md and
skills/trd/SKILL.md. Adding a new one (e.g. skills/erd/SKILL.md with
`metadata.doc_type: erd`) makes it appear here automatically, with zero
changes to this file -- the same "SKILL.md is the source of truth, the
server only discovers and serves it" principle every other tool in this
package follows.

Like get_skill, doc_gen never generates anything itself -- these are
standalone skills (pure instructions, no code path -- see
ARCHITECTURE.md). Its whole job is handing the caller the right, live
instructions to follow; the caller's own model does the actual writing.
"""

from __future__ import annotations

from typing import Any

from .mcp_tools import GeneratedTool
from .registry import parse_skill_md


def doc_type_manifests(manifests) -> dict[str, Any]:
    """Every standalone skill that declared metadata.doc_type, keyed by
    that slug. A skill without the field simply isn't a doc_gen entry --
    this is opt-in, not inferred from being standalone alone (mood is
    standalone but isn't a document template).
    """
    by_doc_type: dict[str, Any] = {}
    for m in manifests:
        if m.kind != "standalone":
            continue
        doc_type = (m.frontmatter.get("metadata") or {}).get("doc_type")
        if doc_type:
            by_doc_type[doc_type] = m
    return by_doc_type


def build_doc_gen_tool(manifests) -> GeneratedTool | None:
    """Returns None (register nothing) if no skill currently declares a
    doc_type -- there's no meaningful empty-enum tool to offer.
    """
    by_doc_type = doc_type_manifests(manifests)
    if not by_doc_type:
        return None

    def handler(arguments: dict[str, Any]) -> dict[str, Any]:
        doc_type = arguments.get("doc_type")
        if not doc_type:
            return {
                "error": {
                    "type": "missing_argument",
                    "message": "doc_type is required.",
                    "available": sorted(by_doc_type),
                }
            }
        manifest = by_doc_type.get(doc_type)
        if manifest is None:
            return {
                "error": {
                    "type": "not_found",
                    "message": f"No document-generation skill for doc_type={doc_type!r}.",
                    "available": sorted(by_doc_type),
                }
            }
        # Re-read live, same as get_skill -- never serve the copy captured at startup.
        frontmatter, body = parse_skill_md(manifest.skill_md_path)
        return {
            "doc_type": doc_type,
            "skill_name": manifest.name,
            "frontmatter": frontmatter,
            "instructions": body,
        }

    schema = {
        "type": "object",
        "properties": {
            "doc_type": {
                "type": "string",
                "enum": sorted(by_doc_type),
                "description": "Which document template's instructions to fetch.",
            }
        },
        "required": ["doc_type"],
    }

    return GeneratedTool(
        name="doc_gen",
        description=(
            "Fetch the live instructions for generating one kind of document "
            f"({', '.join(sorted(by_doc_type))}). Returns the skill's real "
            "SKILL.md instructions verbatim -- follow them to actually produce "
            "the document; this tool does not generate anything itself."
        ),
        parameters=schema,
        handler=handler,
    )
