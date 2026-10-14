from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkflowResult:
    status: str
    output: dict[str, Any] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)
    current_step: str | None = None
    error: dict[str, Any] | None = None


@dataclass
class WorkflowContext:
    inputs: dict[str, Any]
    state: dict[str, Any]
    profiles: dict[str, Any] = field(default_factory=dict)
    error: Any = None
    current_step: str | None = None
    status: str = "RUNNING"
    execution_id: str = ""
