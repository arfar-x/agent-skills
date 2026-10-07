import pytest

from tests.conftest import DIFF_REFS, SAMPLE_DIFF
from lib.diff_position import PositionError, resolve_position

FILE = {"old_path": "a.py", "new_path": "a.py", "diff": SAMPLE_DIFF}


def test_added_line_has_only_new_line():
    pos = resolve_position(FILE, DIFF_REFS, new_line=2)  # added1
    assert pos["new_line"] == 2 and "old_line" not in pos
    assert pos["head_sha"] == "h" and pos["position_type"] == "text"


def test_removed_line_has_only_old_line():
    pos = resolve_position(FILE, DIFF_REFS, old_line=2)
    assert pos["old_line"] == 2 and "new_line" not in pos


def test_context_line_has_both():
    pos = resolve_position(FILE, DIFF_REFS, new_line=4)  # ctx2: old 3, new 4
    assert (pos["old_line"], pos["new_line"]) == (3, 4)


def test_line_outside_hunk():
    with pytest.raises(PositionError, match="not part of the MR diff"):
        resolve_position(FILE, DIFF_REFS, new_line=99)


def test_no_line_given():
    with pytest.raises(PositionError):
        resolve_position(FILE, DIFF_REFS)


def test_multiple_hunks_and_no_newline_marker():
    diff = "@@ -1,1 +1,1 @@\n-a\n+b\n\\ No newline at end of file\n@@ -10,1 +10,2 @@\n x\n+y\n"
    f = {"old_path": "a", "new_path": "a", "diff": diff}
    assert resolve_position(f, DIFF_REFS, new_line=11)["new_line"] == 11
    assert resolve_position(f, DIFF_REFS, old_line=1)["old_line"] == 1
