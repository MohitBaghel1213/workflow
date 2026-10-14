from __future__ import annotations

from typing import Any

from ..errors import WorkflowDefinitionError
from .contracts import StepHandler


class StepHandlerRegistry:
    """Explicit registry mapping declarative step types to their handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, StepHandler] = {}

    def register(self, step_type: str, handler: StepHandler, *, replace: bool = False) -> None:
        if not step_type or not isinstance(step_type, str):
            raise ValueError("step_type must be a non-empty string")
        if step_type in self._handlers and not replace:
            raise ValueError(f"A handler is already registered for step type '{step_type}'")
        self._handlers[step_type] = handler

    def get(self, step_type: str) -> StepHandler:
        try:
            return self._handlers[step_type]
        except KeyError as exc:
            raise WorkflowDefinitionError(f"Unsupported step type: {step_type}") from exc

    def has(self, step_type: str) -> bool:
        return step_type in self._handlers

    def types(self) -> tuple[str, ...]:
        return tuple(sorted(self._handlers))
