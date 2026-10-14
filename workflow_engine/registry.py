from __future__ import annotations

from pathlib import Path
from typing import Any

from .errors import WorkflowNotFoundError
from .loader import load_workflow


class WorkflowRegistry:
    """Resolves workflow IDs to declarative workflow definitions."""

    def __init__(self, definitions: dict[str, dict[str, Any]] | None = None):
        self._definitions: dict[str, dict[str, Any]] = {}
        for definition in (definitions or {}).values():
            self.register(definition)

    def register(self, definition: dict[str, Any]) -> None:
        workflow = definition.get("workflow", {})
        workflow_id = workflow.get("id")
        if not workflow_id:
            raise ValueError("Cannot register workflow without workflow.id")
        self._definitions[workflow_id] = definition

    def load_directory(self, directory: str | Path, recursive: bool = True) -> None:
        directory = Path(directory)
        pattern = "**/*.yaml" if recursive else "*.yaml"
        for path in sorted(directory.glob(pattern)):
            self.register(load_workflow(path))

    def get(self, workflow_id: str) -> dict[str, Any]:
        try:
            return self._definitions[workflow_id]
        except KeyError as exc:
            raise WorkflowNotFoundError(f"Workflow '{workflow_id}' is not registered") from exc

    def ids(self) -> list[str]:
        return sorted(self._definitions)
