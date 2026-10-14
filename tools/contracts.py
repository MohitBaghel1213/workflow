from __future__ import annotations

from typing import Any, Protocol


class ToolHandler(Protocol):
    def execute(self, inputs: dict[str, Any], context: Any) -> Any:
        ...
