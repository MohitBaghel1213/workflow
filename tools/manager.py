from __future__ import annotations

from typing import Any


class ToolManager:
    """Registry and dispatcher for concrete integrations used by capabilities."""

    def __init__(self):
        self._tools: dict[str, Any] = {}

    def register(self, tool_id: str, handler: Any, *, replace: bool = False) -> None:
        if tool_id in self._tools and not replace:
            raise ValueError(f"Tool '{tool_id}' is already registered")
        self._tools[tool_id] = handler

    def execute(self, tool_id: str, inputs: dict[str, Any], context: Any) -> Any:
        try:
            handler = self._tools[tool_id]
        except KeyError as exc:
            raise KeyError(f"Tool '{tool_id}' is not registered") from exc
        return handler.execute(inputs, context)

    def ids(self) -> list[str]:
        return sorted(self._tools)
