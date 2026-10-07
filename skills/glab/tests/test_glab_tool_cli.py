import json
import os
import subprocess
import sys

import importlib.util

_spec = importlib.util.spec_from_file_location("glab_tool", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "glab_tool.py"))
glab_tool = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(glab_tool)

SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "glab_tool.py")


def test_parser_has_no_positionals_and_every_subcommand_has_help():
    parser = glab_tool.build_parser()
    sub = next(a for a in parser._actions if a.dest == "tool")
    helps = {c.dest: c.help for c in sub._choices_actions}
    assert set(sub.choices) - {"whoami"} <= set(helps) and "whoami" in helps
    for name, p in sub.choices.items():
        assert helps[name], name
        assert not [a for a in p._actions if not a.option_strings], f"{name} has a positional"


def test_cli_prints_single_json_and_exits_zero_on_config_error():
    env = {k: v for k, v in os.environ.items() if not k.startswith("GITLAB_")}
    proc = subprocess.run([sys.executable, SCRIPT, "whoami"], capture_output=True, text=True, env=env)
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["error"]["type"] == "configuration_error"


def test_malformed_invocation_exits_nonzero():
    proc = subprocess.run([sys.executable, SCRIPT, "get_mr"], capture_output=True, text=True)
    assert proc.returncode != 0
