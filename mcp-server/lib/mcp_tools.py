"""Turn a toolset's introspected SubcommandSpecs into real fastmcp tools.

Building an explicit JSON Schema directly from each ParamSpec (rather
than deriving one from a Python function's type hints) turned out to be
the robust path here: fastmcp 3.4.7's `Tool.from_function`/`add_tool(fn)`
resolves argument types via `typing.get_type_hints()` against the
function's `__annotations__` dict, not via a synthetic `__signature__`
alone -- confirmed directly against the installed package (a bare
`__signature__` override raised a `KeyError` deep inside pydantic's
schema generation). `Tool`'s own base class exposes `parameters` as a
plain JSON-Schema-dict field, so a small `Tool` subclass with a bound
handler and an explicit schema sidesteps that entirely, verified
end-to-end against the real `fastmcp` package before writing this.
"""

from __future__ import annotations

from typing import Any, Callable

from fastmcp.tools.base import Tool, ToolResult
from pydantic import ConfigDict, Field

from .execute import execute_subcommand
from .introspect import ParamSpec, SubcommandSpec

_JSON_TYPE = {"str": "string", "int": "integer", "float": "number", "bool": "boolean"}


class GeneratedTool(Tool):
    """A tool whose schema and behavior are both built at registration
    time from a toolset's own argparse definition, rather than hand
    written per action.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    handler: Callable[[dict[str, Any]], dict[str, Any]] = Field(exclude=True)

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        return ToolResult(content=self.handler(arguments))


def _json_schema_property(param: ParamSpec) -> dict[str, Any]:
    prop: dict[str, Any] = {"type": _JSON_TYPE[param.kind]}
    if param.choices:
        prop["enum"] = list(param.choices)
    if param.repeated:
        prop = {"type": "array", "items": prop}
    if param.help:
        prop["description"] = param.help
    if not param.required and param.default is not None:
        prop["default"] = param.default
    return prop


def build_input_schema(spec: SubcommandSpec) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {p.name: _json_schema_property(p) for p in spec.params},
        "required": [p.name for p in spec.params if p.required],
    }


def build_tool(toolset: str, manifest, spec: SubcommandSpec) -> GeneratedTool:
    def handler(arguments: dict[str, Any]) -> dict[str, Any]:
        return execute_subcommand(manifest, spec, arguments)

    return GeneratedTool(
        name=f"{toolset}_{spec.name}",
        description=spec.help or f"Run {toolset} {spec.name}.",
        parameters=build_input_schema(spec),
        handler=handler,
    )


def register_toolset_tools(app, manifest, subcommands: list[SubcommandSpec]) -> None:
    for spec in subcommands:
        app.add_tool(build_tool(manifest.toolset, manifest, spec))
