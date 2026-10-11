"""Markdown to Confluence storage format, and the page's Markdown source.

Lets a caller write a page as Markdown instead of hand-written storage
XHTML, deterministically: the same Markdown always renders the same page,
with no model in between to drop a section or reformat an id.

A page can also carry its own Markdown as a collapsed *source block* -- an
``expand`` macro holding a ``code`` macro with the Markdown verbatim. That
block is what makes a partial edit possible later: :mod:`patch_page` reads
the Markdown back, changes only what was asked, and renders the page
again, instead of anyone resending the whole body.

Supported Markdown (deliberately a small, predictable subset): ATX
headings, paragraphs, ``**bold**``, ``*italic*``, `` `code` ``, links,
bulleted and numbered lists (nested by indentation), pipe tables, fenced
code blocks, block quotes, horizontal rules. HTML comments are dropped.
Anything else is kept as plain, escaped text.
"""

from __future__ import annotations

import html
import re
from typing import List, Optional, Tuple

DEFAULT_SOURCE_TITLE = "Markdown source"

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_HR = re.compile(r"^\s{0,3}(?:-{3,}|\*{3,}|_{3,})\s*$")
_FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})\s*([\w+-]*)\s*$")
_LIST_ITEM = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{1,}:?\s*(\|\s*:?-{1,}:?\s*)*\|?\s*$")
_QUOTE = re.compile(r"^\s{0,3}>\s?(.*)$")

_CODE_SPAN = re.compile(r"`([^`]+)`")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITALIC = re.compile(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])")

_SOURCE_BLOCK = re.compile(
    r'<ac:structured-macro ac:name="expand"[^>]*>\s*'
    r'<ac:parameter ac:name="title">(?P<title>.*?)</ac:parameter>\s*'
    r"<ac:rich-text-body>\s*"
    r'<ac:structured-macro ac:name="code"[^>]*>\s*'
    r"(?:<ac:parameter[^>]*>.*?</ac:parameter>\s*)*"
    r"<ac:plain-text-body>(?P<body>.*?)</ac:plain-text-body>\s*"
    r"</ac:structured-macro>\s*</ac:rich-text-body>\s*</ac:structured-macro>",
    re.DOTALL,
)
_CDATA = re.compile(r"<!\[CDATA\[(.*?)\]\]>", re.DOTALL)


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------


def render_page(markdown: str, source_title: Optional[str] = None) -> str:
    """Render ``markdown`` as a page body; with ``source_title``, append the
    Markdown itself as a collapsed source block under that title."""
    body = markdown_to_storage(markdown)
    if source_title:
        body = f"{body}\n{source_block(markdown, source_title)}"
    return body


def markdown_to_storage(markdown: str) -> str:
    """Convert Markdown to Confluence storage-format XHTML."""
    lines = _strip_comments(markdown.replace("\r\n", "\n")).split("\n")
    return "\n".join(_blocks(lines))


def source_block(markdown: str, title: str = DEFAULT_SOURCE_TITLE) -> str:
    """A collapsed ``expand`` macro holding ``markdown`` verbatim."""
    body = markdown.replace("]]>", "]]]]><![CDATA[>")
    return (
        '<ac:structured-macro ac:name="expand">'
        f'<ac:parameter ac:name="title">{_escape(title)}</ac:parameter>'
        "<ac:rich-text-body>"
        '<ac:structured-macro ac:name="code">'
        f"<ac:plain-text-body><![CDATA[{body}]]></ac:plain-text-body>"
        "</ac:structured-macro>"
        "</ac:rich-text-body>"
        "</ac:structured-macro>"
    )


def extract_source(storage: str) -> Optional[Tuple[str, str]]:
    """Return ``(markdown, title)`` from a page body's source block, or
    ``None`` if the page has none. With several, the last one wins."""
    matches = list(_SOURCE_BLOCK.finditer(storage or ""))
    if not matches:
        return None
    match = matches[-1]
    parts = _CDATA.findall(match.group("body"))
    markdown = "".join(parts) if parts else html.unescape(match.group("body"))
    return markdown, html.unescape(match.group("title"))


# ----------------------------------------------------------------------
# Blocks
# ----------------------------------------------------------------------


def _strip_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def _blocks(lines: List[str]) -> List[str]:
    out: List[str] = []
    paragraph: List[str] = []
    i = 0

    def flush() -> None:
        if paragraph:
            out.append(f"<p>{_paragraph(paragraph)}</p>")
            paragraph.clear()

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            flush()
            i += 1
            continue

        fence = _FENCE.match(line)
        if fence:
            flush()
            marker, language = fence.group(1), fence.group(2)
            code: List[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(marker):
                code.append(lines[i])
                i += 1
            i += 1  # closing fence (or end of input)
            out.append(_code_macro("\n".join(code), language))
            continue

        heading = _HEADING.match(line)
        if heading:
            flush()
            level = len(heading.group(1))
            out.append(f"<h{level}>{_inline(heading.group(2))}</h{level}>")
            i += 1
            continue

        if _HR.match(line):
            flush()
            out.append("<hr/>")
            i += 1
            continue

        if "|" in line and i + 1 < len(lines) and _TABLE_SEP.match(lines[i + 1]) and "-" in lines[i + 1]:
            flush()
            rows = [line]
            i += 2
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                rows.append(lines[i])
                i += 1
            out.append(_table(rows))
            continue

        if _QUOTE.match(line):
            flush()
            quoted: List[str] = []
            while i < len(lines) and _QUOTE.match(lines[i]):
                quoted.append(_QUOTE.match(lines[i]).group(1))
                i += 1
            out.append("<blockquote>" + "\n".join(_blocks(quoted)) + "</blockquote>")
            continue

        if _LIST_ITEM.match(line):
            flush()
            items: List[str] = []
            while i < len(lines):
                current = lines[i]
                if _LIST_ITEM.match(current):
                    items.append(current)
                elif current.strip() and current.startswith((" ", "\t")) and items:
                    items[-1] = f"{items[-1]} {current.strip()}"
                else:
                    break
                i += 1
            out.append(_list(items))
            continue

        paragraph.append(line)
        i += 1

    flush()
    return out


def _paragraph(lines: List[str]) -> str:
    parts: List[str] = []
    for index, line in enumerate(lines):
        hard_break = line.endswith("  ") and index < len(lines) - 1
        parts.append(_inline(line.strip()) + ("<br/>" if hard_break else ""))
    return " ".join(parts).replace("<br/> ", "<br/>")


def _code_macro(code: str, language: str) -> str:
    parameter = f'<ac:parameter ac:name="language">{_escape(language)}</ac:parameter>' if language else ""
    body = code.replace("]]>", "]]]]><![CDATA[>")
    return (
        f'<ac:structured-macro ac:name="code">{parameter}'
        f"<ac:plain-text-body><![CDATA[{body}]]></ac:plain-text-body>"
        "</ac:structured-macro>"
    )


def _table(rows: List[str]) -> str:
    def cells(row: str) -> List[str]:
        row = row.strip()
        if row.startswith("|"):
            row = row[1:]
        if row.endswith("|"):
            row = row[:-1]
        return [cell.strip() for cell in row.split("|")]

    header, body = cells(rows[0]), [cells(r) for r in rows[1:]]
    html_rows = ["<tr>" + "".join(f"<th>{_inline(c)}</th>" for c in header) + "</tr>"]
    for row in body:
        html_rows.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in row) + "</tr>")
    return "<table><tbody>" + "".join(html_rows) + "</tbody></table>"


def _list(items: List[str]) -> str:
    """Nested lists from indentation: deeper items open a child list
    inside the previous item."""
    out: List[str] = []
    stack: List[Tuple[int, str]] = []  # (indent, tag)

    for raw in items:
        match = _LIST_ITEM.match(raw)
        indent = len(match.group(1).expandtabs(4))
        tag = "ol" if match.group(2)[0].isdigit() else "ul"
        text = _inline(match.group(3))

        while stack and indent < stack[-1][0]:
            out.append(f"</li></{stack.pop()[1]}>")
        if stack and indent == stack[-1][0]:
            if tag != stack[-1][1]:
                out.append(f"</li></{stack.pop()[1]}><{tag}><li>")
                stack.append((indent, tag))
            else:
                out.append("</li><li>")
        else:
            out.append(f"<{tag}><li>")
            stack.append((indent, tag))
        out.append(text)

    while stack:
        out.append(f"</li></{stack.pop()[1]}>")
    return "".join(out)


# ----------------------------------------------------------------------
# Inline
# ----------------------------------------------------------------------


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _inline(text: str) -> str:
    """Escape, then apply inline Markdown. Code spans are protected first
    so nothing inside them is formatted."""
    spans: List[str] = []

    def keep(match: re.Match) -> str:
        spans.append(f"<code>{_escape(match.group(1))}</code>")
        return f"\x00{len(spans) - 1}\x00"

    text = _CODE_SPAN.sub(keep, text)
    text = _escape(text)
    text = _LINK.sub(lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', text)
    text = _BOLD.sub(r"<strong>\1</strong>", text)
    text = _ITALIC.sub(r"<em>\1</em>", text)
    return re.sub(r"\x00(\d+)\x00", lambda m: spans[int(m.group(1))], text)
