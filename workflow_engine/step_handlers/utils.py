from __future__ import annotations

from typing import Any

from ..errors import WorkflowDefinitionError, WorkflowExecutionError
from ..expression import interpolate
from .contracts import StepExecutionContext


def resolve(value: Any, context: StepExecutionContext) -> Any:
    workflow_context = context.workflow_context
    return interpolate(
        value,
        workflow_context.inputs,
        workflow_context.state,
        context.schemas,
        workflow_context.error,
        context.profiles,
    )


def set_path(root: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    if parts and parts[0] == "state":
        parts = parts[1:]
    if not parts:
        raise WorkflowDefinitionError("Cannot set an empty path")
    current = root
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    current[parts[-1]] = value


def get_path(root: dict[str, Any], path: str) -> Any:
    parts = path.split(".")
    if parts and parts[0] == "state":
        parts = parts[1:]
    value: Any = root
    for part in parts:
        value = value[part]
    return value


def apply_output_mapping(value: Any, output_spec: dict[str, Any], context: StepExecutionContext) -> None:
    state = context.workflow_context.state
    if "target" in output_spec:
        set_path(state, output_spec["target"], value)
    elif "mapping" in output_spec:
        if not isinstance(value, dict):
            raise WorkflowExecutionError("Output mapping requires a dictionary result")
        for source, target in output_spec["mapping"].items():
            set_path(state, target, value.get(source))
