from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from ..capabilities.executor import CapabilityExecutor
from ..models import WorkflowContext, WorkflowResult
from ..registry import WorkflowRegistry
from ..runtime import RuntimeAdapter


@dataclass
class StepOutcome:
    """Normalized result of one step execution."""

    next_step: str | None = None
    workflow_result: WorkflowResult | None = None


@dataclass
class StepExecutionContext:
    """Dependencies and execution data available to every step handler."""

    workflow: dict[str, Any]
    workflow_context: WorkflowContext
    runtime: RuntimeAdapter
    capability_executor: CapabilityExecutor
    workflow_registry: WorkflowRegistry
    profiles: dict[str, Any]
    schemas: dict[str, Any]
    create_engine: Callable[[dict[str, Any]], Any]


class StepHandler(Protocol):
    """Contract implemented by each supported declarative step type."""

    def validate(self, step: dict[str, Any]) -> None:
        """Validate step-type-specific structure or raise WorkflowDefinitionError."""
        ...

    def execute(
        self, step: dict[str, Any], context: StepExecutionContext
    ) -> StepOutcome:
        ...
