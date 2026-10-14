from __future__ import annotations

from typing import Any

from ..errors import WorkflowDefinitionError
from .registry import StepHandlerRegistry


class WorkflowValidator:
    """Validates workflow-wide invariants separately from step implementations."""

    @staticmethod
    def possible_next_steps(step: dict[str, Any]) -> list[str]:
        targets: list[str] = []
        if isinstance(step.get("next"), str):
            targets.append(step["next"])
        for key in ("on_success", "on_failure", "on_response", "on_exhausted", "otherwise"):
            value = step.get(key)
            if isinstance(value, dict) and isinstance(value.get("next"), str):
                targets.append(value["next"])
        for condition in step.get("conditions", []) or []:
            if isinstance(condition, dict) and isinstance(condition.get("next"), str):
                targets.append(condition["next"])
        return targets

    def validate(self, definition: dict[str, Any], step_registry: StepHandlerRegistry) -> None:
        workflow = definition.get("workflow")
        if not isinstance(workflow, dict):
            raise WorkflowDefinitionError("Workflow definition must contain a workflow object")
        if not workflow.get("id"):
            raise WorkflowDefinitionError("workflow.id is required")
        if not workflow.get("version"):
            raise WorkflowDefinitionError("workflow.version is required")
        raw_steps = workflow.get("steps", [])
        if not isinstance(raw_steps, list) or not raw_steps:
            raise WorkflowDefinitionError("workflow.steps must be a non-empty list")

        seen: set[str] = set()
        for step in raw_steps:
            if not isinstance(step, dict):
                raise WorkflowDefinitionError("Every workflow step must be an object")
            step_id = step.get("id")
            if not step_id:
                raise WorkflowDefinitionError("Every workflow step must have an id")
            if step_id in seen:
                raise WorkflowDefinitionError(f"Duplicate step id '{step_id}'")
            seen.add(step_id)
            step_type = step.get("type")
            if not step_type:
                raise WorkflowDefinitionError(f"Step '{step_id}' has no type")
            handler = step_registry.get(step_type)
            handler.validate(step)

        step_ids = {step["id"] for step in raw_steps}
        for step in raw_steps:
            for target in self.possible_next_steps(step):
                if target not in step_ids:
                    raise WorkflowDefinitionError(
                        f"Step '{step['id']}' references unknown next step '{target}'"
                    )

        start_at = workflow.get("start_at")
        if start_at and start_at not in step_ids:
            raise WorkflowDefinitionError(f"workflow.start_at references unknown step '{start_at}'")
