"""Covers shapes jira_tool.py never exercises: action="append" (send_bulk
--to) and a custom `type=` callable (--no-seen's _bool_arg). Runs against
the REAL skills/telegram/scripts/telegram_tool.py.
"""

from pathlib import Path

from lib.introspect import introspect_subcommands, load_build_parser

TELEGRAM_SCRIPT = Path(__file__).resolve().parents[2] / "skills" / "telegram" / "scripts" / "telegram_tool.py"


def _specs():
    build_parser = load_build_parser(TELEGRAM_SCRIPT)
    return {s.name: s for s in introspect_subcommands(build_parser())}


def test_send_bulk_to_is_repeated_and_required():
    params = {p.name: p for p in _specs()["send_bulk"].params}
    assert params["to"].repeated is True
    assert params["to"].required is True
    assert params["to"].flag == "--to"


def test_no_seen_custom_type_falls_back_to_str_not_a_crash():
    params = {p.name: p for p in _specs()["search_messages"].params}
    assert params["no_seen"].kind == "str"
    assert params["no_seen"].flag == "--no-seen"
    assert params["no_seen"].default is True
    assert params["no_seen"].required is False


def test_confirm_flag_is_boolean_on_every_subcommand():
    specs = _specs()
    for name in ("whoami", "send_message", "send_bulk", "forward_message"):
        params = {p.name: p for p in specs[name].params}
        assert params["confirm"].kind == "bool"
        assert params["confirm"].default is False
