"""Walk a toolset's ``build_parser()`` into typed subcommand specs.

Every toolset in this repo (`skills/jira/scripts/jira_tool.py`,
`skills/telegram/scripts/telegram_tool.py`, ...) already defines its full
CLI surface as a plain `argparse` dispatcher: one `add_subparsers()` at
the top, one `add_parser(name, help=...)` per action, typed
`add_argument(...)` calls underneath. That shape is a complete,
already-accurate schema for each action -- this module reads it directly
instead of hand-duplicating it, so the generated MCP tools can never
drift from what the CLI itself actually accepts.

Reliance on `argparse`'s underscore-prefixed attributes (`_subparsers`,
`_choices_actions`, `_StoreTrueAction`, ...) is deliberate and stable --
that shape hasn't changed across Python's stdlib in over a decade -- but
it is not a public API. `IntrospectionError` exists so a genuinely
unexpected shape fails loudly at startup instead of silently producing a
wrong or missing tool.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

ParamKind = Literal["str", "int", "float", "bool"]

_TYPE_MAP: dict[Any, ParamKind] = {None: "str", str: "str", int: "int", float: "float"}


class IntrospectionError(RuntimeError):
    """A toolset's build_parser() didn't match the shape this module
    depends on. Callers (lib/registry.py) catch this per-toolset so one
    unusual toolset doesn't prevent every other toolset's tools from
    registering.
    """


@dataclass(frozen=True)
class ParamSpec:
    name: str  # argparse `dest`, e.g. "issue_key" or "no_seen" -- valid as a Python/JSON identifier
    flag: str  # the actual long flag to pass on argv, e.g. "--issue_key" or "--no-seen"
    kind: ParamKind
    required: bool
    default: Any
    choices: tuple[str, ...] | None
    repeated: bool  # argparse action="append" -- flag repeats once per list element
    help: str | None


@dataclass(frozen=True)
class SubcommandSpec:
    name: str  # e.g. "worklog"
    help: str | None
    params: tuple[ParamSpec, ...] = field(default_factory=tuple)


def _param_from_action(action: argparse.Action) -> ParamSpec | None:
    if isinstance(action, argparse._HelpAction):
        return None
    if not action.option_strings:
        raise IntrospectionError(
            f"Positional argument {action.dest!r} is not supported by the dynamic "
            "tool generator -- every CLI subcommand argument must be a --flag so "
            "it can map to a named MCP tool parameter."
        )
    flag = max(action.option_strings, key=len)  # prefer the long form, e.g. --issue_key over -i

    repeated = isinstance(action, argparse._AppendAction)
    is_bool_flag = isinstance(action, (argparse._StoreTrueAction, argparse._StoreFalseAction))

    if is_bool_flag:
        kind: ParamKind = "bool"
    elif action.type in _TYPE_MAP:
        kind = _TYPE_MAP[action.type]
    else:
        # A custom `type=` callable (e.g. telegram_tool.py's `_bool_arg`, which
        # parses "true"/"false"/"1"/"0"/"yes"/"no" strings). We don't try to
        # infer its semantics -- the underlying CLI already validates/converts
        # the raw string itself when it runs, so passing the string through
        # untouched is safe. Surfacing this as a plain string keeps one
        # unusual flag from taking down the rest of its subcommand's schema.
        kind = "str"

    choices = tuple(action.choices) if action.choices else None

    return ParamSpec(
        name=action.dest,
        flag=flag,
        kind=kind,
        required=bool(action.required) and not is_bool_flag,
        default=False if is_bool_flag else action.default,
        choices=choices,
        repeated=repeated,
        help=action.help,
    )


def introspect_subcommands(parser: argparse.ArgumentParser) -> list[SubcommandSpec]:
    """Walk one toolset's build_parser() output into SubcommandSpecs."""
    try:
        group_actions = parser._subparsers._group_actions  # type: ignore[union-attr]
        sub_action = next(a for a in group_actions if isinstance(a, argparse._SubParsersAction))
    except (AttributeError, StopIteration) as exc:
        raise IntrospectionError(
            "build_parser() did not return a parser with add_subparsers(...) at "
            "the top level -- the dynamic tool generator requires the same shape "
            "as skills/jira/scripts/jira_tool.py."
        ) from exc

    help_by_name = {a.dest: a.help for a in sub_action._choices_actions}  # type: ignore[attr-defined]

    specs: list[SubcommandSpec] = []
    for name, subparser in sub_action.choices.items():
        params: list[ParamSpec] = []
        for action in subparser._actions:
            p = _param_from_action(action)
            if p is not None:
                params.append(p)
        specs.append(SubcommandSpec(name=name, help=help_by_name.get(name), params=tuple(params)))
    return specs


_SHARED_PACKAGE_NAMES = ("tools", "lib")  # the layout every toolset in this repo uses -- this
                                            # package (mcp-server/lib/) happens to share the name


def _pop_shared_packages() -> dict[str, Any]:
    """Remove and return any sys.modules entries under the shared
    tools/lib package names (and their submodules), so a fresh import
    can resolve against whichever toolset root is on sys.path right now
    instead of a previous toolset's cached module -- or, just as
    importantly, instead of *this very package* (mcp-server/lib/ is
    itself named `lib`, and is quite possibly the module currently
    executing this function). The caller must restore the returned dict
    into sys.modules once done -- see load_build_parser's finally block.
    """
    popped: dict[str, Any] = {}
    for name in list(sys.modules):
        if name in _SHARED_PACKAGE_NAMES or any(
            name.startswith(f"{prefix}.") for prefix in _SHARED_PACKAGE_NAMES
        ):
            popped[name] = sys.modules.pop(name)
    return popped


def load_build_parser(script_path: Path):
    """Import a toolset's scripts/<x>_tool.py as an isolated module and
    return its build_parser callable.

    Uses spec_from_file_location (not import_module) so the dispatcher
    module itself never collides across toolsets in sys.modules. Only the
    target toolset's own root is put on sys.path, and only for the
    duration of the import -- mirroring jira_tool.py's own
    `sys.path.insert(0, _SKILL_ROOT)` pattern, which every toolset's CLI
    dispatcher relies on to find its own `tools`/`lib` packages. Those
    packages are imported under their plain, shared names inside the
    toolset's own script (`from tools import ...`) -- resolved against
    sys.modules before sys.path is even consulted -- so this package's
    own same-named `lib` (and any previously-imported toolset's `tools`/
    `lib`) are popped out of sys.modules first and put back afterward,
    regardless of outcome.
    """
    module_name = f"_agent_skills_mcp_tool_{script_path.parent.parent.name}"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise IntrospectionError(f"Could not load {script_path} as a module.")
    module = importlib.util.module_from_spec(spec)

    skill_root = str(script_path.parent.parent)
    saved = _pop_shared_packages()
    sys.path.insert(0, skill_root)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise IntrospectionError(f"Importing {script_path} raised: {exc}") from exc
    finally:
        sys.path.remove(skill_root)
        _pop_shared_packages()  # discard whatever the toolset's script imported under tools/lib
        sys.modules.update(saved)  # restore this process's own tools/lib (notably our own `lib`)

    if not hasattr(module, "build_parser"):
        raise IntrospectionError(f"{script_path} has no build_parser() function.")
    return module.build_parser
