from unittest.mock import MagicMock, patch

from lib.markdown_storage import extract_source, render_page
from tools import create_page, patch_page, update_page

MARKDOWN = "# Spec\n\n**Status**: Draft\n\n## Limits\n\n- cap 50\n"
TITLE = "Spec Kit source (spec.md)"


def _client(body=None, labels=("spec-draft",), auto_confirm=False):
    client = MagicMock()
    client.config.auto_confirm_writes = auto_confirm
    client.get_page_storage.return_value = {
        "id": "7",
        "title": "Spec",
        "space_key": "ENG",
        "version": 4,
        "body_storage": render_page(MARKDOWN, TITLE) if body is None else body,
        "labels": list(labels),
        "url": "https://wiki/7",
    }
    client.update_page.return_value.to_dict.return_value = {"id": "7", "version": 5}
    client.add_labels.side_effect = lambda _id, names: list(labels) + names
    return client


def test_patch_page_asks_first_and_shows_a_diff():
    client = _client()
    with patch("tools.patch_page.get_client", return_value=client):
        result = patch_page.patch_page("7", find=["cap 50"], replace=["cap 100"], add_labels=["spec-approved"])
    action = result["pending_action"]
    assert result["requires_confirmation"] is True
    assert "-- cap 50" in action["diff"] and "+- cap 100" in action["diff"]
    assert action["add_labels"] == ["spec-approved"] and action["version"] == 4
    client.update_page.assert_not_called()


def test_patch_page_writes_only_the_change_pinned_to_the_read_version():
    client = _client()
    with patch("tools.patch_page.get_client", return_value=client):
        result = patch_page.patch_page(
            "7",
            find=["**Status**: Draft"],
            replace=["**Status**: Approved (revision 1)"],
            section=["Limits"],
            section_markdown=["- cap 100"],
            add_labels=["spec-approved"],
            remove_labels=["spec-draft"],
            confirm=True,
        )
    args, kwargs = client.update_page.call_args
    assert kwargs["version"] == 5 and args == ("7",)
    markdown, title = extract_source(kwargs["body_storage"])
    assert title == TITLE
    assert "Approved (revision 1)" in markdown and "cap 100" in markdown and "cap 50" not in markdown
    client.add_labels.assert_called_once_with("7", ["spec-approved"])
    client.remove_label.assert_called_once_with("7", "spec-draft")
    assert result["labels"] == ["spec-approved"]
    assert [edit["edit"] for edit in result["edits"]] == ["replace_text", "replace_section"]


def test_patch_page_labels_only_does_not_rewrite_the_page():
    client = _client()
    with patch("tools.patch_page.get_client", return_value=client):
        patch_page.patch_page("7", add_labels=["x"], confirm=True)
    client.update_page.assert_not_called()
    client.add_labels.assert_called_once_with("7", ["x"])


def test_patch_page_without_a_source_block_is_refused():
    client = _client(body="<p>hand written</p>")
    with patch("tools.patch_page.get_client", return_value=client):
        result = patch_page.patch_page("7", find=["a"], replace=["b"], confirm=True)
    assert result["error"]["type"] == "invalid_input"
    assert "no Markdown source block" in result["error"]["message"]


def test_patch_page_reports_an_inexact_edit_and_writes_nothing():
    client = _client()
    with patch("tools.patch_page.get_client", return_value=client):
        result = patch_page.patch_page("7", find=["missing"], replace=["x"], confirm=True)
    assert result["error"]["type"] == "invalid_input"
    client.update_page.assert_not_called()


def test_patch_page_needs_something_to_do_and_consistent_labels():
    assert patch_page.patch_page("7")["error"]["type"] == "invalid_input"
    result = patch_page.patch_page("7", add_labels=["a"], remove_labels=["a"])
    assert result["error"]["type"] == "invalid_input"


def test_create_page_renders_markdown_with_source_and_labels():
    client = MagicMock()
    client.config.auto_confirm_writes = False
    client.create_page.return_value.id = "9"
    client.create_page.return_value.to_dict.return_value = {"id": "9"}
    client.add_labels.return_value = ["spec-draft"]
    with patch("tools.create_page.get_client", return_value=client):
        result = create_page.create_page(
            "ENG", "Spec", body_markdown=MARKDOWN, source_title=TITLE, labels=["spec-draft"], confirm=True
        )
    body = client.create_page.call_args.args[2]
    assert body.startswith("<h1>Spec</h1>") and extract_source(body) == (MARKDOWN, TITLE)
    assert result["labels"] == ["spec-draft"]


def test_create_page_needs_exactly_one_body():
    assert create_page.create_page("ENG", "T")["error"]["type"] == "invalid_input"
    both = create_page.create_page("ENG", "T", body_storage="<p>x</p>", body_markdown="x")
    assert both["error"]["type"] == "invalid_input"


def test_update_page_renders_markdown():
    client = MagicMock()
    client.config.auto_confirm_writes = True
    client.update_page.return_value.to_dict.return_value = {"id": "7"}
    with patch("tools.update_page.get_client", return_value=client):
        update_page.update_page("7", body_markdown="# New", source_title=TITLE)
    body = client.update_page.call_args.kwargs["body_storage"]
    assert extract_source(body) == ("# New", TITLE)


def test_update_page_rejects_two_bodies():
    result = update_page.update_page("7", body_storage="<p>x</p>", body_markdown="x")
    assert result["error"]["type"] == "invalid_input"
