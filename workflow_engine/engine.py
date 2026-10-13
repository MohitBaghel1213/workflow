from __future__ import annotations

from copy import deepcopy
from typing import Any

from .errors import WorkflowDefinitionError
from .expression import evaluate, interpolate
from .models import WorkflowContext, WorkflowResult
from .runtime import Runtime


class WorkflowEngine:
    """
    Executes the framework-neutral workflow specification.

    The engine owns:
      - graph traversal
      - state
      - deterministic routing
      - state updates
      - retries
      - terminal results

    The Runtime owns:
      - LLM/agent execution
      - tool execution
      - HITL transport
    """

    def __init__(self, definition: dict[str, Any], runtime: Runtime):
        self.definition = definition
        self.runtime = runtime
        self.workflow = definition["workflow"]
        self.steps = {step["id"]: step for step in self.workflow["steps"]}
        self.schemas = self.workflow.get("schemas", {})
        self.policies = self.workflow.get("policies", {})
        self._validate_definition()

    def _validate_definition(self) -> None:
        if not self.workflow.get("id"):
            raise WorkflowDefinitionError("workflow.id is required")
        if not self.workflow.get("version"):
            raise WorkflowDefinitionError("workflow.version is required")
        if not self.steps:
            raise WorkflowDefinitionError("workflow.steps must not be empty")

        for step in self.steps.values():
            step_type = step.get("type")
            if not step_type:
                raise WorkflowDefinitionError(f"Step {step['id']} has no type")
            if step_type == "capability" and not step.get("capability"):
                raise WorkflowDefinitionError(f"Capability step {step['id']} has no capability")
            if step_type == "condition" and not step.get("conditions"):
                raise WorkflowDefinitionError(f"Condition step {step['id']} has no conditions")

    def initial_context(self, inputs: dict[str, Any]) -> WorkflowContext:
        state = {}
        for name, spec in self.workflow.get("state", {}).items():
            state[name] = deepcopy(spec.get("default"))
        return WorkflowContext(inputs=deepcopy(inputs), state=state)

    def run(self, inputs: dict[str, Any]) -> WorkflowResult:
        context = self.initial_context(inputs)
        first_step = self.workflow["steps"][0]["id"]
        return self.run_from(context, first_step)

    def run_from(self, context: WorkflowContext, step_id: str) -> WorkflowResult:
        current = step_id
        max_steps = self.policies.get("execution_limits", {}).get("max_total_steps", 50)

        while current:
            context.current_step = current
            context.state.setdefault("execution", {})
            context.state["execution"]["total_steps"] = (
                context.state["execution"].get("total_steps", 0) + 1
            )

            if context.state["execution"]["total_steps"] > max_steps:
                return WorkflowResult(
                    status="FAILED",
                    output={"error": {"code": "MAX_STEPS_EXCEEDED"}},
                    state=context.state,
                    current_step=current,
                )

            step = self.steps[current]
            result = self._execute_step(step, context)

            if isinstance(result, WorkflowResult):
                return result

            current = result

        return WorkflowResult(
            status="COMPLETED",
            state=context.state,
            current_step=context.current_step,
        )

    def _execute_step(self, step: dict[str, Any], context: WorkflowContext):
        step_type = step["type"]

        if step_type == "capability":
            return self._execute_capability(step, context)

        if step_type == "condition":
            return self._execute_condition(step, context)

        if step_type == "human_input":
            return self._execute_human_input(step, context)

        if step_type == "state_update":
            self._execute_state_update(step, context)
            return step.get("next")

        if step_type == "retry":
            # Retry is represented as a bounded counter at the engine layer.
            # A runtime may additionally implement provider-level retries.
            attempts = context.state.setdefault("_retry_attempts", {})
            count = attempts.get(step["id"], 0) + 1
            attempts[step["id"]] = count
            max_attempts = step.get("policy", {}).get("max_attempts", 3)
            if count <= max_attempts:
                return step["next"]
            return step.get("on_exhausted", {}).get("next")

        if step_type == "terminal":
            status = step.get("status", "COMPLETED")
            output = interpolate(
                step.get("output", {}),
                context.inputs,
                context.state,
                self.schemas,
                context.error,
            )
            return WorkflowResult(
                status=status,
                output=output,
                state=context.state,
                current_step=step["id"],
            )

        raise WorkflowDefinitionError(f"Unsupported step type: {step_type}")

    def _execute_capability(self, step: dict[str, Any], context: WorkflowContext):
        capability = step["capability"]
        inputs = interpolate(
            step.get("input", {}),
            context.inputs,
            context.state,
            self.schemas,
            context.error,
        )

        try:
            result = self.runtime.invoke_capability(
                capability=capability,
                inputs=inputs,
                context={
                    "workflow_id": self.workflow["id"],
                    "workflow_version": self.workflow["version"],
                    "state": context.state,
                },
            )
            context.error = None
        except Exception as exc:
            context.error = {
                "type": type(exc).__name__,
                "message": str(exc),
            }
            return step.get("on_failure", {}).get("next")

        output = step.get("output", {})
        if "target" in output:
            _set_path(context.state, output["target"], result)
        elif "mapping" in output:
            for source, target in output["mapping"].items():
                _set_path(context.state, target, result.get(source))

        return step.get("on_success", {}).get("next")

    def _execute_condition(self, step: dict[str, Any], context: WorkflowContext):
        for condition in step.get("conditions", []):
            if evaluate(
                condition["when"],
                context.inputs,
                context.state,
                self.schemas,
                context.error,
            ):
                return condition["next"]
        return step.get("otherwise", {}).get("next")

    def _execute_human_input(self, step: dict[str, Any], context: WorkflowContext):
        prompt = interpolate(
            step["prompt"]["message"],
            context.inputs,
            context.state,
            self.schemas,
            context.error,
        )
        response = self.runtime.request_human_input(
            prompt=prompt,
            context={
                "workflow_id": self.workflow["id"],
                "workflow_version": self.workflow["version"],
                "step_id": step["id"],
                "state": context.state,
            },
        )
        target = step["output"]["target"]
        _set_path(context.state, target, response)
        return step["on_response"]["next"]

    def _execute_state_update(self, step: dict[str, Any], context: WorkflowContext):
        for operation in step.get("operations", []):
            target = operation["target"]
            value = interpolate(
                operation.get("value"),
                context.inputs,
                context.state,
                self.schemas,
                context.error,
            )

            if operation["operation"] == "merge":
                existing = _get_path(context.state, target) or {}
                _set_path(context.state, target, {**existing, **value})
            elif operation["operation"] == "append_to_input":
                path = target.removeprefix("input.")
                current = context.inputs.get(path, "")
                context.inputs[path] = f"{current}\n\n{value}".strip()
            else:
                raise WorkflowDefinitionError(
                    f"Unsupported state operation: {operation['operation']}"
                )


def _split_path(path: str) -> list[str]:
    return path.split(".")


def _get_path(root: dict[str, Any], path: str) -> Any:
    parts = _split_path(path)
    if parts and parts[0] == "state":
        parts = parts[1:]
    value = root
    for part in parts:
        value = value[part]
    return value


def _set_path(root: dict[str, Any], path: str, value: Any) -> None:
    parts = _split_path(path)
    if parts and parts[0] == "state":
        parts = parts[1:]

    current = root
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    current[parts[-1]] = value
