from dataclasses import replace

import pytest

from lib.confluence_client import (
    ConfluenceAuthError,
    ConfluenceClient,
    ConfluenceNotFoundError,
    ConfluenceRateLimitError,
    ConfluenceValidationError,
)

from .conftest import make_response


# ----------------------------------------------------------------------
# Deployment-type -> REST path dispatch
# ----------------------------------------------------------------------


def test_server_deployment_uses_rest_api_path(confluence_config, confluence_credential, mock_session):
    client = ConfluenceClient(config=confluence_config, credential=confluence_credential, session=mock_session)
    assert client._api_path == "/rest/api"
    assert client._web_prefix == ""


def test_cloud_deployment_uses_wiki_rest_api_path(confluence_config_cloud, confluence_credential, mock_session):
    client = ConfluenceClient(config=confluence_config_cloud, credential=confluence_credential, session=mock_session)
    assert client._api_path == "/wiki/rest/api"
    assert client._web_prefix == "/wiki"


def test_get_page_requests_the_deployment_specific_path(client, mock_session):
    mock_session.request.return_value = make_response(
        json_data={"id": "123", "title": "T", "version": {"number": 1}, "space": {"key": "ENG"}}
    )
    client.get_page("123")
    args, kwargs = mock_session.request.call_args
    assert args[1] == "https://confluence.example.com/rest/api/content/123"


def test_get_page_cloud_requests_wiki_prefixed_path(confluence_config_cloud, confluence_credential, mock_session):
    client = ConfluenceClient(config=confluence_config_cloud, credential=confluence_credential, session=mock_session)
    mock_session.request.return_value = make_response(
        json_data={"id": "123", "title": "T", "version": {"number": 1}, "space": {"key": "ENG"}}
    )
    client.get_page("123")
    args, kwargs = mock_session.request.call_args
    assert args[1] == "https://example.atlassian.net/wiki/rest/api/content/123"


# ----------------------------------------------------------------------
# Error mapping
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "status,exc_type",
    [
        (401, ConfluenceAuthError),
        (403, ConfluenceAuthError),
        (404, ConfluenceNotFoundError),
        (400, ConfluenceValidationError),
        (409, ConfluenceValidationError),
        (429, ConfluenceRateLimitError),
    ],
)
def test_error_status_codes_map_to_typed_exceptions(client, mock_session, status, exc_type):
    mock_session.request.return_value = make_response(status_code=status, json_data={"message": "boom"})
    with pytest.raises(exc_type) as excinfo:
        client.get_page("123")
    assert excinfo.value.status_code == status


def test_500_maps_to_base_api_error(client, mock_session):
    from lib.confluence_client import ConfluenceApiError

    mock_session.request.return_value = make_response(status_code=500, json_data={"message": "boom"})
    with pytest.raises(ConfluenceApiError):
        client.get_page("123")


# ----------------------------------------------------------------------
# Model building
# ----------------------------------------------------------------------


def test_build_page_extracts_fields_and_plain_text_body(client, mock_session):
    mock_session.request.return_value = make_response(
        json_data={
            "id": "123",
            "title": "My Page",
            "version": {"number": 4, "when": "2026-01-01T00:00:00.000Z"},
            "space": {"key": "ENG"},
            "body": {"storage": {"value": "<p>Hello</p>"}},
            "ancestors": [{"id": "1", "title": "Root"}, {"id": "2", "title": "Parent"}],
            "history": {"createdDate": "2025-12-01T00:00:00.000Z"},
            "_links": {"webui": "/spaces/ENG/pages/123/My+Page"},
        }
    )
    page = client.get_page("123")
    assert page.id == "123"
    assert page.title == "My Page"
    assert page.version == 4
    assert page.space_key == "ENG"
    assert page.body_plain_text == "Hello"
    assert page.parent_id == "2"
    assert len(page.ancestors) == 2
    assert page.url == "https://confluence.example.com/spaces/ENG/pages/123/My+Page"


def test_build_space_extracts_fields(client, mock_session):
    mock_session.request.return_value = make_response(
        json_data={
            "key": "ENG",
            "name": "Engineering",
            "description": {"plain": {"value": "Engineering space"}},
            "_links": {"webui": "/spaces/ENG"},
        }
    )
    space = client.get_space("ENG")
    assert space.key == "ENG"
    assert space.name == "Engineering"
    assert space.description == "Engineering space"
    assert space.url == "https://confluence.example.com/spaces/ENG"


# ----------------------------------------------------------------------
# Pagination
# ----------------------------------------------------------------------


def test_paginate_stops_when_links_next_is_absent(client, mock_session):
    mock_session.request.return_value = make_response(
        json_data={"results": [{"key": "A"}, {"key": "B"}], "size": 2, "_links": {}}
    )
    spaces = client.list_spaces()
    assert len(spaces) == 2
    assert mock_session.request.call_count == 1


def test_paginate_walks_multiple_pages(client, mock_session):
    first = make_response(
        json_data={"results": [{"key": "A"}] * 25, "size": 25, "_links": {"next": "/rest/api/space?start=25"}}
    )
    second = make_response(json_data={"results": [{"key": "B"}] * 5, "size": 5, "_links": {}})
    mock_session.request.side_effect = [first, second]
    spaces = client.list_spaces()
    assert len(spaces) == 30
    assert mock_session.request.call_count == 2


def test_paginate_respects_max_results_total(client, mock_session):
    mock_session.request.return_value = make_response(
        json_data={"results": [{"key": "A"}] * 25, "size": 25, "_links": {"next": "/rest/api/space?start=25"}}
    )
    spaces = client.list_spaces(max_results=10)
    assert len(spaces) == 10


# ----------------------------------------------------------------------
# create_page / update_page / delete_page
# ----------------------------------------------------------------------


def _page_json(**overrides):
    base = {
        "id": "999",
        "title": "New Page",
        "version": {"number": 1},
        "space": {"key": "ENG"},
        "body": {"storage": {"value": "<p>Hi</p>"}},
    }
    base.update(overrides)
    return base


def test_create_page_sends_storage_body_and_refetches(client, mock_session):
    create_response = make_response(json_data={"id": "999"})
    fetch_response = make_response(json_data=_page_json())
    mock_session.request.side_effect = [create_response, fetch_response]

    page = client.create_page("ENG", "New Page", "<p>Hi</p>")

    assert page.id == "999"
    create_call = mock_session.request.call_args_list[0]
    assert create_call.kwargs["json"]["body"]["storage"]["representation"] == "storage"
    assert create_call.kwargs["json"]["space"]["key"] == "ENG"


def test_create_page_requires_body_storage(client):
    with pytest.raises(ConfluenceValidationError):
        client.create_page("ENG", "Title", "")


def test_create_page_includes_parent_id_as_ancestor(client, mock_session):
    mock_session.request.side_effect = [make_response(json_data={"id": "999"}), make_response(json_data=_page_json())]
    client.create_page("ENG", "New Page", "<p>Hi</p>", parent_id="42")
    create_call = mock_session.request.call_args_list[0]
    assert create_call.kwargs["json"]["ancestors"] == [{"id": "42"}]


def test_update_page_auto_increments_version(client, mock_session):
    current = make_response(json_data={"title": "Old", "version": {"number": 5}})
    updated = make_response(json_data=_page_json(version={"number": 6}, title="New Title"))
    mock_session.request.side_effect = [current, updated]

    page = client.update_page("999", title="New Title")

    update_call = mock_session.request.call_args_list[1]
    assert update_call.kwargs["json"]["version"]["number"] == 6
    assert page.version == 6


def test_update_page_requires_title_or_body(client):
    with pytest.raises(ConfluenceValidationError):
        client.update_page("999")


def test_delete_page_calls_delete(client, mock_session):
    mock_session.request.return_value = make_response(status_code=204)
    client.delete_page("999")
    args, kwargs = mock_session.request.call_args
    assert args[0] == "DELETE"


# ----------------------------------------------------------------------
# Comments and labels
# ----------------------------------------------------------------------


def test_add_comment_builds_from_request_body_not_response(client, mock_session):
    mock_session.request.return_value = make_response(
        json_data={"id": "555", "history": {"createdBy": {"displayName": "Alice"}, "createdDate": "2026-01-01"}}
    )
    comment = client.add_comment("999", "<p>A comment</p>")
    assert comment.id == "555"
    assert comment.author == "Alice"
    assert comment.body_plain_text == "A comment"


def test_add_label_sends_array_body(client, mock_session):
    mock_session.request.return_value = make_response(json_data={"results": [{"name": "onboarding"}]})
    labels = client.add_label("999", "onboarding")
    assert labels == ["onboarding"]
    call = mock_session.request.call_args
    assert call.kwargs["json"] == [{"prefix": "global", "name": "onboarding"}]


def test_remove_label_calls_delete_with_label_in_path(client, mock_session):
    mock_session.request.return_value = make_response(status_code=204)
    client.remove_label("999", "onboarding")
    args, kwargs = mock_session.request.call_args
    assert args[0] == "DELETE"
    assert args[1].endswith("/content/999/label/onboarding")


# ----------------------------------------------------------------------
# resolve_space / my_pages / get_page_by_title
# ----------------------------------------------------------------------


def test_resolve_space_falls_back_to_default(confluence_config, confluence_credential, mock_session):
    config = replace(confluence_config, default_space="ENG")
    client = ConfluenceClient(config=config, credential=confluence_credential, session=mock_session)
    assert client.resolve_space() == "ENG"
    assert client.resolve_space("OTHER") == "OTHER"


def test_resolve_space_returns_none_when_unset(client):
    assert client.resolve_space() is None


def test_get_page_by_title_returns_none_when_no_match(client, mock_session):
    mock_session.request.return_value = make_response(json_data={"results": []})
    assert client.get_page_by_title("ENG", "Nonexistent") is None


def test_my_pages_uses_current_user_cql(client, mock_session):
    mock_session.request.return_value = make_response(json_data={"results": [], "size": 0, "_links": {}})
    client.my_pages()
    call = mock_session.request.call_args
    assert call.kwargs["params"]["cql"] == "creator = currentUser() order by lastmodified desc"
