import pytest

from lib.markdown_patch import PatchError, apply_patch, replace_section

DOC = """# Spec

**Status**: Draft

## Stories

### Story 1

old body
```
## not a heading
```

### Story 2

keep

## Requirements

- **FR-001**: cap 50
"""


def test_text_replacement_must_match_exactly_once():
    text, records = apply_patch(DOC, finds=["cap 50"], replaces=["cap 100"])
    assert "cap 100" in text and "cap 50" not in text
    assert records == [{"edit": "replace_text", "find": "cap 50", "replace": "cap 100", "count": 1}]


def test_missing_or_ambiguous_text_fails():
    with pytest.raises(PatchError, match="not found"):
        apply_patch(DOC, finds=["nope"], replaces=["x"])
    with pytest.raises(PatchError, match="ambiguous"):
        apply_patch(DOC, finds=["Story"], replaces=["x"])


def test_replace_all_is_explicit():
    text, records = apply_patch(DOC, finds=["Story"], replaces=["Item"], replace_all=True)
    assert "Story" not in text and records[0]["count"] == 2


def test_unpaired_edits_fail():
    with pytest.raises(PatchError, match="pairs"):
        apply_patch(DOC, finds=["a", "b"], replaces=["x"])
    with pytest.raises(PatchError, match="pairs"):
        apply_patch(DOC, section_headings=["Story 1"], section_bodies=[])


def test_section_replacement_keeps_heading_and_stops_at_same_level():
    text = replace_section(DOC, "### Story 1", "new body")
    assert "### Story 1\n\nnew body\n\n### Story 2" in text
    assert "old body" not in text and "## not a heading" not in text
    assert "keep" in text


def test_headings_inside_code_fences_are_ignored():
    with pytest.raises(PatchError, match="not found"):
        replace_section(DOC, "not a heading", "x")


def test_section_runs_to_the_next_heading_of_same_or_higher_level():
    text = replace_section(DOC, "Stories", "collapsed")
    assert "Story 1" not in text and "Story 2" not in text
    assert "## Stories\n\ncollapsed\n\n## Requirements" in text


def test_missing_or_ambiguous_heading_fails():
    with pytest.raises(PatchError, match="not found"):
        replace_section(DOC, "Nope", "x")
    with pytest.raises(PatchError, match="ambiguous"):
        replace_section(DOC + "\n## Stories\n", "Stories", "x")
