from __future__ import annotations

import time
from typing import Any

from ..capabilities.contracts import ExecutionContext
from ..errors import WorkflowDefinitionError
from ..expression import evaluate
from ..models import WorkflowResult
from .contracts import StepExecutionContext, StepOutcome
from .utils import apply_output_mapping, get_path, resolve, set_path


class BaseStepHandler:
    def validate(self, step: dict[str, Any]) -> None:
        """Default: no extra validation beyond graph-level checks."""

    @staticmethod
    def require(step: dict[str, Any], path: str, message: str | None = None) -> Any:
        value: Any = step
        for part in path.split("."):
            if not isinstance(value, dict) or part not in value:
                raise WorkflowDefinitionError(message or f"Step '{step.get('id', '<unknown>')}' requires '{path}'")
            value = value[part]
        if value is None or value == "":
            raise WorkflowDefinitionError(message or f"Step '{step.get('id', '<unknown>')}' requires '{path}'")
        return value


class CapabilityStepHandler(BaseStepHandler):
    def validate(self, step: dict[str, Any]) -> None:
        self.require(step, "capability")

    def execute(self, step: dict[str, Any], context: StepExecutionContext) -> StepOutcome:
        workflow = context.workflow
        wf_context = context.workflow_context
        capability_id = step["capability"]
        allowed = workflow.get("capabilities", {}).get("allowed")
        if allowed is not None and capability_id not in allowed:
            wf_context.error = {
                "type": "CapabilityNotAllowedError",
                "message": f"Capability '{capability_id}' is not allowed by workflow",
            }
            return StepOutcome(next_step=step.get("on_failure", {}).get("next"))

        inputs = resolve(step.get("input", {}), context)
        execution_context = ExecutionContext(
            workflow_id=workflow["id"],
            workflow_version=workflow["version"],
            execution_id=wf_context.execution_id,
            step_id=step["id"],
            runtime_name=context.runtime.runtime_name,
            state=wf_context.state,
            services={},
            config=step.get("config", {}),
        )
        try:
            result = context.capability_executor.execute(capability_id, inputs, execution_context)
            if not result.success:
                wf_context.error = result.error or {
                    "type": "CapabilityExecutionError",
                    "message": f"Capability '{capability_id}' failed",
                }
                return StepOutcome(next_step=step.get("on_failure", {}).get("next"))
            wf_context.error = None
            apply_output_mapping(result.output, step.get("output", {}), context)
        except Exception as exc:
            wf_context.error = {"type": type(exc).__name__, "message": str(exc)}
            return StepOutcome(next_step=step.get("on_failure", {}).get("next"))
        return StepOutcome(next_step=step.get("on_success", {}).get("next"))


class ConditionStepHandler(BaseStepHandler):
    def validate(self, step: dict[str, Any]) -> None:
        conditions = self.require(step, "conditions")
        if not isinstance(conditions, list) or not conditions:
            raise WorkflowDefinitionError(f"Condition step '{step.get('id')}' must define a non-empty conditions list")
        for index, condition in enumerate(conditions):
            if not isinstance(condition, dict) or not condition.get("when") or not condition.get("next"):
                raise WorkflowDefinitionError(f"Condition step '{step.get('id')}' has an invalid condition at index {index}")

    def execute(self, step: dict[str, Any], context: StepExecutionContext) -> StepOutcome:
        wf_context = context.workflow_context
        for condition in step.get("conditions", []):
            if evaluate(
                condition["when"], wf_context.inputs, wf_context.state,
                context.schemas, wf_context.error, context.profiles,
            ):
                return StepOutcome(next_step=condition["next"])
        return StepOutcome(next_step=step.get("otherwise", {}).get("next"))


class HumanInputStepHandler(BaseStepHandler):
    def validate(self, step: dict[str, Any]) -> None:
        self.require(step, "prompt.message")
        self.require(step, "output.target")
        self.require(step, "on_response.next")

    def execute(self, step: dict[str, Any], context: StepExecutionContext) -> StepOutcome:
        wf_context = context.workflow_context
        prompt = resolve(step["prompt"]["message"], context)
        response = context.runtime.request_human_input(prompt, {
            "workflow_id": context.workflow["id"],
            "workflow_version": context.workflow["version"],
            "execution_id": wf_context.execution_id,
            "step_id": step["id"],
            "state": wf_context.state,
        })
        set_path(wf_context.state, step["output"]["target"], response)
        return StepOutcome(next_step=step["on_response"]["next"])


class StateUpdateStepHandler(BaseStepHandler):
    _SUPPORTED_OPERATIONS = {"merge", "append_to_input", "set"}

    def validate(self, step: dict[str, Any]) -> None:
        operations = self.require(step, "operations")
        if not isinstance(operations, list) or not operations:
            raise WorkflowDefinitionError(f"State-update step '{step.get('id')}' must define a non-empty operations list")
        for index, operation in enumerate(operations):
            if not isinstance(operation, dict) or operation.get("operation") not in self._SUPPORTED_OPERATIONS:
                raise WorkflowDefinitionError(f"State-update step '{step.get('id')}' has unsupported operation at index {index}")
            if not operation.get("target"):
                raise WorkflowDefinitionError(f"State-update step '{step.get('id')}' operation {index} requires target")

    def execute(self, step: dict[str, Any], context: StepExecutionContext) -> StepOutcome:
        wf_context = context.workflow_context
        for operation in step.get("operations", []):
            target = operation["target"]
            value = resolve(operation.get("value"), context)
            op = operation["operation"]
            if op == "merge":
                existing = get_path(wf_context.state, target) or {}
                if not isinstance(existing, dict) or not isinstance(value, dict):
                    raise WorkflowDefinitionError("merge operation requires dictionary target and value")
                set_path(wf_context.state, target, {**existing, **value})
            elif op == "append_to_input":
                path = target.removeprefix("input.")
                current = wf_context.inputs.get(path, "")
                wf_context.inputs[path] = f"{current}\n\n{value}".strip()
            elif op == "set":
                set_path(wf_context.state, target, value)
        return StepOutcome(next_step=step.get("next"))


class RetryStepHandler(BaseStepHandler):
    def validate(self, step: dict[str, Any]) -> None:
        self.require(step, "next")
        max_attempts = step.get("policy", {}).get("max_attempts", 3)
        if not isinstance(max_attempts, int) or max_attempts < 0:
            raise WorkflowDefinitionError(f"Retry step '{step.get('id')}' policy.max_attempts must be a non-negative integer")

    def execute(self, step: dict[str, Any], context: StepExecutionContext) -> StepOutcome:
        state = context.workflow_context.state
        attempts = state.setdefault("_retry_attempts", {})
        count = attempts.get(step["id"], 0) + 1
        attempts[step["id"]] = count
        policy = step.get("policy", {})
        max_attempts = policy.get("max_attempts", 3)
        if count <= max_attempts:
            backoff = policy.get("backoff", {})
            strategy = backoff.get("strategy", "none")
            initial = float(backoff.get("initial_delay_seconds", 0))
            maximum = float(backoff.get("maximum_delay_seconds", initial or 0))
            if strategy == "exponential" and initial > 0:
                time.sleep(min(initial * (2 ** (count - 1)), maximum or initial))
            elif strategy == "constant" and initial > 0:
                time.sleep(min(initial, maximum or initial))
            return StepOutcome(next_step=step["next"])
        return StepOutcome(next_step=step.get("on_exhausted", {}).get("next"))


class SubworkflowStepHandler(BaseStepHandler):
    def validate(self, step: dict[str, Any]) -> None:
        self.require(step, "workflow")

    def execute(self, step: dict[str, Any], context: StepExecutionContext) -> StepOutcome:
        wf_context = context.workflow_context
        try:
            child_definition = context.workflow_registry.get(step["workflow"])
            child_inputs = resolve(step.get("input", {}), context)
            child = context.create_engine(child_definition)
            child_result = child.run(child_inputs, execution_id=wf_context.execution_id)
        except Exception as exc:
            wf_context.error = {"type": type(exc).__name__, "message": str(exc)}
            return StepOutcome(next_step=step.get("on_failure", {}).get("next"))
        if child_result.status != "COMPLETED":
            wf_context.error = child_result.error or child_result.output.get("error") or {
                "type": "SubWorkflowFailed",
                "message": f"Sub-workflow '{step['workflow']}' returned {child_result.status}",
            }
            return StepOutcome(next_step=step.get("on_failure", {}).get("next"))
        wf_context.error = None
        apply_output_mapping(child_result.output, step.get("output", {}), context)
        return StepOutcome(next_step=step.get("on_success", {}).get("next"))


class TerminalStepHandler(BaseStepHandler):
    def execute(self, step: dict[str, Any], context: StepExecutionContext) -> StepOutcome:
        wf_context = context.workflow_context
        output = resolve(step.get("output", {}), context)
        return StepOutcome(workflow_result=WorkflowResult(
            status=step.get("status", "COMPLETED"),
            output=output,
            state=wf_context.state,
            current_step=step["id"],
            error=wf_context.error,
        ))
