from lib.markdown_storage import (
    DEFAULT_SOURCE_TITLE,
    extract_source,
    markdown_to_storage,
    render_page,
    source_block,
)


def test_headings_paragraphs_and_inline_formatting():
    out = markdown_to_storage("# Title\n\nSome **bold**, *em* and `a<b` text.")
    assert out == (
        "<h1>Title</h1>\n"
        "<p>Some <strong>bold</strong>, <em>em</em> and <code>a&lt;b</code> text.</p>"
    )


def test_text_is_escaped_and_links_kept():
    out = markdown_to_storage("a < b & [site](https://x.y/?a=1&b=2)")
    assert out == '<p>a &lt; b &amp; <a href="https://x.y/?a=1&amp;b=2">site</a></p>'


def test_code_span_contents_are_not_formatted():
    assert markdown_to_storage("`**not bold**`") == "<p><code>**not bold**</code></p>"


def test_lists_nest_by_indentation_and_switch_type():
    out = markdown_to_storage("- a\n  - b\n- c\n\n1. one\n2. two")
    assert out == (
        "<ul><li>a<ul><li>b</li></ul></li><li>c</li></ul>\n"
        "<ol><li>one</li><li>two</li></ol>"
    )


def test_pipe_table_has_header_row():
    out = markdown_to_storage("| ID | Text |\n|---|---|\n| FR-001 | MUST |")
    assert out == (
        "<table><tbody><tr><th>ID</th><th>Text</th></tr>"
        "<tr><td>FR-001</td><td>MUST</td></tr></tbody></table>"
    )


def test_fenced_code_becomes_a_code_macro_and_survives_cdata_end():
    out = markdown_to_storage("```bash\necho ']]>'\n# not a heading\n```")
    assert out.startswith('<ac:structured-macro ac:name="code"><ac:parameter ac:name="language">bash')
    assert "<h1>" not in out
    assert "]]]]><![CDATA[>" in out


def test_comments_dropped_and_rules_and_quotes_rendered():
    out = markdown_to_storage("<!-- hidden -->\n---\n> quoted")
    assert out == "<hr/>\n<blockquote><p>quoted</p></blockquote>"


def test_persian_text_passes_through_unchanged():
    assert markdown_to_storage("## اسپک ذخیره فیلترها") == "<h2>اسپک ذخیره فیلترها</h2>"


def test_source_block_round_trips_the_markdown_and_title():
    markdown = "# T\n\nWith ]]> inside and `code`.\n"
    page = render_page(markdown, "Spec Kit source (spec.md)")
    assert extract_source(page) == (markdown, "Spec Kit source (spec.md)")


def test_render_without_source_title_adds_no_block():
    assert extract_source(render_page("# T")) is None


def test_extract_tolerates_confluence_added_attributes_and_takes_the_last_block():
    stored = source_block("first", "A").replace(
        'ac:name="expand">', 'ac:name="expand" ac:schema-version="1" ac:macro-id="x">'
    ) + source_block("second", DEFAULT_SOURCE_TITLE)
    assert extract_source(stored) == ("second", DEFAULT_SOURCE_TITLE)
