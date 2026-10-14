from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ExecutionContext:
    workflow_id: str
    workflow_version: str
    execution_id: str
    step_id: str
    runtime_name: str
    state: dict[str, Any]
    services: dict[str, Any] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class CapabilityResult:
    """Normalized capability response.

    `success=False` represents an execution error. A domain result such as
    validation_status=INVALID is still a successful execution.
    """

    success: bool = True
    output: Any = None
    error: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class CapabilityHandler(Protocol):
    def execute(self, inputs: dict[str, Any], context: ExecutionContext) -> Any:
        ...
