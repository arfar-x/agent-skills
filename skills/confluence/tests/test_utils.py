from lib.utils import safe_get, storage_to_plain_text


def test_storage_to_plain_text_strips_tags():
    assert storage_to_plain_text("<p>Hello <strong>world</strong></p>") == "Hello world"


def test_storage_to_plain_text_separates_paragraphs_with_blank_line():
    result = storage_to_plain_text("<p>First</p><p>Second</p>")
    assert result == "First\n\nSecond"


def test_storage_to_plain_text_unescapes_entities():
    assert storage_to_plain_text("<p>Fish &amp; chips</p>") == "Fish & chips"


def test_storage_to_plain_text_handles_none_and_empty():
    assert storage_to_plain_text(None) == ""
    assert storage_to_plain_text("") == ""


def test_storage_to_plain_text_strips_macro_tags():
    value = '<ac:structured-macro ac:name="info"><ac:rich-text-body><p>Note</p></ac:rich-text-body></ac:structured-macro>'
    result = storage_to_plain_text(value)
    assert "Note" in result
    assert "<ac:" not in result


def test_safe_get_walks_nested_dict():
    data = {"a": {"b": {"c": 1}}}
    assert safe_get(data, "a", "b", "c") == 1


def test_safe_get_returns_default_on_missing_key():
    assert safe_get({"a": 1}, "b", "c", default="fallback") == "fallback"


def test_safe_get_returns_default_when_not_a_dict():
    assert safe_get({"a": "not-a-dict"}, "a", "b", default="fallback") == "fallback"
