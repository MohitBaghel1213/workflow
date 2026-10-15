from __future__ import annotations

from typing import Any


class ToolManager:
    """Registry for callable tools plus schemas exposed to an agent runtime."""

    def __init__(self):
        self._tools: dict[str, dict[str, Any]] = {}

    def register(
        self,
        tool_id: str,
        handler: Any,
        *,
        description: str = "",
        input_schema: dict[str, Any] | None = None,
        replace: bool = False,
    ) -> None:
        if tool_id in self._tools and not replace:
            raise ValueError(f"Tool '{tool_id}' is already registered")
        self._tools[tool_id] = {
            "handler": handler,
            "description": description,
            "input_schema": input_schema or {"type": "object", "properties": {}},
        }

    def execute(self, tool_id: str, inputs: dict[str, Any], context: Any) -> Any:
        try:
            handler = self._tools[tool_id]["handler"]
        except KeyError as exc:
            raise KeyError(f"Tool '{tool_id}' is not registered") from exc
        return handler.execute(inputs, context)

    def definitions(self, tool_ids: list[str] | None = None) -> list[dict[str, Any]]:
        """Return model-facing tool descriptions, optionally allowlisted."""
        selected = tool_ids if tool_ids is not None else sorted(self._tools)
        definitions = []
        for tool_id in selected:
            if tool_id not in self._tools:
                raise KeyError(f"Tool '{tool_id}' is not registered")
            entry = self._tools[tool_id]
            definitions.append({
                "name": tool_id,
                "description": entry["description"],
                "input_schema": entry["input_schema"],
            })
        return definitions

    def ids(self) -> list[str]:
        return sorted(self._tools)


# Public terminology alias: this object is both the tool registry and dispatcher.
ToolRegistry = ToolManager
