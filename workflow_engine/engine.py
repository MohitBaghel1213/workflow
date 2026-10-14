from __future__ import annotations

from copy import deepcopy
from uuid import uuid4
from typing import Any

from .bootstrap import build_capability_executor
from .capabilities.executor import CapabilityExecutor
from .errors import WorkflowDefinitionError, WorkflowExecutionError
from .models import WorkflowContext, WorkflowResult
from .registry import WorkflowRegistry
from .runtime import RuntimeAdapter
from .step_handlers import (
    StepExecutionContext,
    StepHandlerRegistry,
    StepOutcome,
    WorkflowValidator,
    build_step_handler_registry,
)


class WorkflowEngine:
    """Framework-independent workflow orchestrator.

    The engine owns execution lifecycle, state initialization, execution limits,
    and graph traversal. Step-specific behavior is delegated to registered
    StepHandler implementations. Business capabilities are delegated to the
    shared CapabilityExecutor.
    """

    def __init__(
        self,
        definition: dict[str, Any],
        runtime: RuntimeAdapter,
        *,
        capability_executor: CapabilityExecutor | None = None,
        workflow_registry: WorkflowRegistry | None = None,
        profiles: dict[str, Any] | None = None,
        step_handler_registry: StepHandlerRegistry | None = None,
        workflow_validator: WorkflowValidator | None = None,
    ):
        self.definition = definition
        self.runtime = runtime
        self.workflow = definition.get("workflow", {})
        self.schemas = self.workflow.get("schemas", {})
        self.policies = self.workflow.get("policies", {})
        self.profiles = profiles or {}
        self.workflow_registry = workflow_registry or WorkflowRegistry(
            {self.workflow.get("id", "workflow"): definition}
        )
        self.capability_executor = capability_executor or build_capability_executor(runtime)
        self.step_handler_registry = step_handler_registry or build_step_handler_registry()
        self.workflow_validator = workflow_validator or WorkflowValidator()
        self.workflow_validator.validate(definition, self.step_handler_registry)
        self.steps = {step["id"]: step for step in self.workflow["steps"]}

    def initial_context(
        self, inputs: dict[str, Any], execution_id: str | None = None
    ) -> WorkflowContext:
        self._validate_inputs(inputs)
        state = {
            name: deepcopy(spec.get("default"))
            for name, spec in self.workflow.get("state", {}).items()
        }
        return WorkflowContext(
            inputs=deepcopy(inputs),
            state=state,
            profiles=self.profiles,
            execution_id=execution_id or str(uuid4()),
        )

    def _validate_inputs(self, inputs: dict[str, Any]) -> None:
        schema = self.workflow.get("input", {}).get("schema", {})
        missing = [name for name in schema.get("required", []) if name not in inputs]
        if missing:
            raise WorkflowExecutionError(f"Missing required workflow inputs: {missing}")
        for name, spec in schema.get("properties", {}).items():
            if name not in inputs:
                continue
            value = inputs[name]
            expected = spec.get("type")
            checks = {
                "string": lambda item: isinstance(item, str),
                "object": lambda item: isinstance(item, dict),
                "array": lambda item: isinstance(item, list),
                "boolean": lambda item: isinstance(item, bool),
                "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
                "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
            }
            if expected in checks and not checks[expected](value):
                raise WorkflowExecutionError(f"Input '{name}' must be of type {expected}")
            if expected == "string" and spec.get("min_length") and len(value) < spec["min_length"]:
                raise WorkflowExecutionError(f"Input '{name}' must not be empty")

    def run(self, inputs: dict[str, Any], *, execution_id: str | None = None) -> WorkflowResult:
        context = self.initial_context(inputs, execution_id)
        first_step = self.workflow.get("start_at") or self.workflow["steps"][0]["id"]
        return self.run_from(context, first_step)

    def run_from(self, context: WorkflowContext, step_id: str) -> WorkflowResult:
        current: str | None = step_id
        max_steps = self.policies.get("execution_limits", {}).get("max_total_steps", 100)
        while current:
            if current not in self.steps:
                raise WorkflowDefinitionError(f"Unknown current step '{current}'")
            context.current_step = current
            execution = context.state.setdefault("execution", {})
            execution["total_steps"] = execution.get("total_steps", 0) + 1
            if execution["total_steps"] > max_steps:
                return WorkflowResult(
                    status="FAILED",
                    output={"error": {
                        "code": "MAX_STEPS_EXCEEDED",
                        "message": "Workflow exceeded max_total_steps",
                    }},
                    state=context.state,
                    current_step=current,
                )

            step = self.steps[current]
            iteration_group = step.get("iteration_group")
            if iteration_group:
                counter_key = f"{iteration_group}_iterations"
                execution[counter_key] = execution.get(counter_key, 0) + 1
                limit_key = f"max_{iteration_group}_iterations"
                limit = self.policies.get("execution_limits", {}).get(limit_key)
                if limit is not None and execution[counter_key] > limit:
                    return WorkflowResult(
                        status="FAILED",
                        output={"error": {
                            "code": "ITERATION_LIMIT_EXCEEDED",
                            "group": iteration_group,
                            "limit": limit,
                        }},
                        state=context.state,
                        current_step=current,
                    )

            outcome = self._execute_step(step, context)
            if outcome.workflow_result is not None:
                return outcome.workflow_result
            current = outcome.next_step

        return WorkflowResult(
            status="COMPLETED", state=context.state, current_step=context.current_step
        )

    def _execute_step(self, step: dict[str, Any], context: WorkflowContext) -> StepOutcome:
        """Dispatch generically; this method must not branch on step type."""
        handler = self.step_handler_registry.get(step["type"])
        handler_context = StepExecutionContext(
            workflow=self.workflow,
            workflow_context=context,
            runtime=self.runtime,
            capability_executor=self.capability_executor,
            workflow_registry=self.workflow_registry,
            profiles=self.profiles,
            schemas=self.schemas,
            create_engine=self._create_child_engine,
        )
        outcome = handler.execute(step, handler_context)
        if not isinstance(outcome, StepOutcome):
            raise WorkflowExecutionError(
                f"Handler for step type '{step['type']}' must return StepOutcome"
            )
        return outcome

    def _create_child_engine(self, definition: dict[str, Any]) -> "WorkflowEngine":
        """Create a child engine while reusing the parent's shared registries/services."""
        return WorkflowEngine(
            definition,
            self.runtime,
            capability_executor=self.capability_executor,
            workflow_registry=self.workflow_registry,
            profiles=self.profiles,
            step_handler_registry=self.step_handler_registry,
            workflow_validator=self.workflow_validator,
        )
