from unittest.mock import MagicMock, patch

from tools import (
    add_comment,
    add_label,
    create_page,
    delete_page,
    get_attachments,
    get_children,
    get_comments,
    get_labels,
    get_page,
    get_page_by_title,
    get_space,
    list_spaces,
    my_pages,
    page_summary,
    remove_label,
    search,
    update_page,
)


def _mock_client(auto_confirm_writes=False):
    client = MagicMock()
    client.config.auto_confirm_writes = auto_confirm_writes
    return client


# ----------------------------------------------------------------------
# Read tools
# ----------------------------------------------------------------------


def test_get_page_returns_page_dict():
    mock_client = _mock_client()
    mock_client.get_page.return_value.to_dict.return_value = {"id": "1", "title": "T"}
    with patch("tools.get_page.get_client", return_value=mock_client):
        result = get_page.get_page("1")
    assert result == {"page": {"id": "1", "title": "T"}}


def test_get_page_rejects_empty_page_id():
    result = get_page.get_page("")
    assert result["error"]["type"] == "invalid_input"


def test_get_page_by_title_returns_none_when_not_found():
    mock_client = _mock_client()
    mock_client.get_page_by_title.return_value = None
    with patch("tools.get_page_by_title.get_client", return_value=mock_client):
        result = get_page_by_title.get_page_by_title("ENG", "Nope")
    assert result == {"page": None}


def test_search_returns_count_and_pages():
    mock_client = _mock_client()
    page = MagicMock()
    page.to_dict.return_value = {"id": "1"}
    mock_client.search.return_value = [page]
    with patch("tools.search.get_client", return_value=mock_client):
        result = search.search("space = ENG")
    assert result["count"] == 1
    assert result["pages"] == [{"id": "1"}]


def test_search_rejects_empty_cql():
    result = search.search("")
    assert result["error"]["type"] == "invalid_input"


def test_list_spaces_returns_spaces():
    mock_client = _mock_client()
    space = MagicMock()
    space.to_dict.return_value = {"key": "ENG"}
    mock_client.list_spaces.return_value = [space]
    with patch("tools.list_spaces.get_client", return_value=mock_client):
        result = list_spaces.list_spaces()
    assert result == {"count": 1, "spaces": [{"key": "ENG"}]}


def test_get_space_returns_space():
    mock_client = _mock_client()
    mock_client.get_space.return_value.to_dict.return_value = {"key": "ENG"}
    with patch("tools.get_space.get_client", return_value=mock_client):
        result = get_space.get_space("ENG")
    assert result == {"space": {"key": "ENG"}}


def test_get_comments_returns_list():
    mock_client = _mock_client()
    comment = MagicMock()
    comment.to_dict.return_value = {"id": "c1"}
    mock_client.get_comments.return_value = [comment]
    with patch("tools.get_comments.get_client", return_value=mock_client):
        result = get_comments.get_comments("1")
    assert result == {"page_id": "1", "count": 1, "comments": [{"id": "c1"}]}


def test_get_attachments_returns_list():
    mock_client = _mock_client()
    mock_client.get_attachments.return_value = []
    with patch("tools.get_attachments.get_client", return_value=mock_client):
        result = get_attachments.get_attachments("1")
    assert result == {"page_id": "1", "count": 0, "attachments": []}


def test_get_children_returns_list():
    mock_client = _mock_client()
    mock_client.get_children.return_value = []
    with patch("tools.get_children.get_client", return_value=mock_client):
        result = get_children.get_children("1")
    assert result == {"page_id": "1", "count": 0, "children": []}


def test_get_labels_returns_labels():
    mock_client = _mock_client()
    mock_client.get_labels.return_value = ["onboarding"]
    with patch("tools.get_labels.get_client", return_value=mock_client):
        result = get_labels.get_labels("1")
    assert result == {"page_id": "1", "labels": ["onboarding"]}


def test_page_summary_defaults_to_all_sections():
    mock_client = _mock_client()
    mock_client.get_page.return_value.to_dict.return_value = {"id": "1"}
    mock_client.get_comments.return_value = []
    mock_client.get_attachments.return_value = []
    mock_client.get_labels.return_value = []
    mock_client.get_children.return_value = []
    with patch("tools.page_summary.get_client", return_value=mock_client):
        result = page_summary.page_summary("1")
    assert set(result.keys()) == {"page", "comments", "attachments", "labels", "children"}


def test_page_summary_rejects_unknown_section():
    result = page_summary.page_summary("1", sections=["bogus"])
    assert result["error"]["type"] == "invalid_input"


def test_page_summary_only_fetches_requested_sections():
    mock_client = _mock_client()
    mock_client.get_page.return_value.to_dict.return_value = {"id": "1"}
    with patch("tools.page_summary.get_client", return_value=mock_client):
        result = page_summary.page_summary("1", sections=["page"])
    assert list(result.keys()) == ["page"]
    mock_client.get_comments.assert_not_called()


def test_my_pages_returns_list():
    mock_client = _mock_client()
    mock_client.my_pages.return_value = []
    with patch("tools.my_pages.get_client", return_value=mock_client):
        result = my_pages.my_pages()
    assert result == {"count": 0, "pages": []}


# ----------------------------------------------------------------------
# Write tools -- confirmation gate
# ----------------------------------------------------------------------


def test_create_page_requires_confirmation_by_default():
    mock_client = _mock_client(auto_confirm_writes=False)
    with patch("tools.create_page.get_client", return_value=mock_client):
        result = create_page.create_page("ENG", "Title", "<p>Hi</p>")
    assert result["confirmed"] is False
    assert result["requires_confirmation"] is True
    mock_client.create_page.assert_not_called()


def test_create_page_executes_when_confirmed():
    mock_client = _mock_client(auto_confirm_writes=False)
    mock_client.create_page.return_value.to_dict.return_value = {"id": "1"}
    with patch("tools.create_page.get_client", return_value=mock_client):
        result = create_page.create_page("ENG", "Title", "<p>Hi</p>", confirm=True)
    assert result["confirmed"] is True
    mock_client.create_page.assert_called_once()


def test_create_page_executes_when_auto_confirm_enabled():
    mock_client = _mock_client(auto_confirm_writes=True)
    mock_client.create_page.return_value.to_dict.return_value = {"id": "1"}
    with patch("tools.create_page.get_client", return_value=mock_client):
        result = create_page.create_page("ENG", "Title", "<p>Hi</p>")
    assert result["confirmed"] is True


def test_update_page_requires_confirmation_by_default():
    mock_client = _mock_client()
    with patch("tools.update_page.get_client", return_value=mock_client):
        result = update_page.update_page("1", title="New")
    assert result["requires_confirmation"] is True
    mock_client.update_page.assert_not_called()


def test_update_page_rejects_when_no_field_given():
    mock_client = _mock_client(auto_confirm_writes=True)
    with patch("tools.update_page.get_client", return_value=mock_client):
        result = update_page.update_page("1")
    assert result["error"]["type"] == "invalid_input"


def test_delete_page_requires_confirmation_by_default():
    mock_client = _mock_client()
    with patch("tools.delete_page.get_client", return_value=mock_client):
        result = delete_page.delete_page("1")
    assert result["requires_confirmation"] is True
    mock_client.delete_page.assert_not_called()


def test_delete_page_executes_when_confirmed():
    mock_client = _mock_client()
    with patch("tools.delete_page.get_client", return_value=mock_client):
        result = delete_page.delete_page("1", confirm=True)
    assert result == {"confirmed": True, "page_id": "1", "deleted": True}
    mock_client.delete_page.assert_called_once_with("1")


def test_add_comment_requires_confirmation_by_default():
    mock_client = _mock_client()
    with patch("tools.add_comment.get_client", return_value=mock_client):
        result = add_comment.add_comment("1", "<p>Hi</p>")
    assert result["requires_confirmation"] is True
    mock_client.add_comment.assert_not_called()


def test_add_label_requires_confirmation_by_default():
    mock_client = _mock_client()
    with patch("tools.add_label.get_client", return_value=mock_client):
        result = add_label.add_label("1", "onboarding")
    assert result["requires_confirmation"] is True
    mock_client.add_label.assert_not_called()


def test_add_label_executes_when_confirmed():
    mock_client = _mock_client()
    mock_client.add_label.return_value = ["onboarding"]
    with patch("tools.add_label.get_client", return_value=mock_client):
        result = add_label.add_label("1", "onboarding", confirm=True)
    assert result == {"confirmed": True, "page_id": "1", "labels": ["onboarding"]}


def test_remove_label_requires_confirmation_by_default():
    mock_client = _mock_client()
    with patch("tools.remove_label.get_client", return_value=mock_client):
        result = remove_label.remove_label("1", "onboarding")
    assert result["requires_confirmation"] is True
    mock_client.remove_label.assert_not_called()


def test_remove_label_executes_when_confirmed():
    mock_client = _mock_client()
    with patch("tools.remove_label.get_client", return_value=mock_client):
        result = remove_label.remove_label("1", "onboarding", confirm=True)
    assert result == {"confirmed": True, "page_id": "1", "removed": "onboarding"}
