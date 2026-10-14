from __future__ import annotations

import pytest

from runtimes.mock_runtime import MockRuntime
from workflow_engine import (
    StepHandlerRegistry,
    StepOutcome,
    WorkflowEngine,
    WorkflowDefinitionError,
    build_capability_executor,
    build_step_handler_registry,
)


class CustomStepHandler:
    """Example extension: no changes to WorkflowEngine are required."""

    def validate(self, step):
        if "next" not in step:
            raise WorkflowDefinitionError("custom step requires next")

    def execute(self, step, context):
        context.workflow_context.state["custom_step_executed"] = True
        return StepOutcome(next_step=step["next"])


def minimal_definition(steps):
    return {
        "api_version": "1.0",
        "workflow": {
            "id": "registry-test",
            "name": "Registry Test",
            "version": "1.0.0",
            "input": {"schema": {"type": "object", "properties": {}}},
            "state": {"custom_step_executed": {"type": "boolean", "default": False}},
            "steps": steps,
        },
    }


def test_custom_step_type_can_be_registered_without_changing_engine():
    registry = build_step_handler_registry()
    registry.register("custom", CustomStepHandler())
    definition = minimal_definition([
        {"id": "custom_step", "type": "custom", "next": "done"},
        {"id": "done", "type": "terminal", "status": "COMPLETED", "output": {"ok": True}},
    ])
    runtime = MockRuntime()
    engine = WorkflowEngine(
        definition,
        runtime,
        capability_executor=build_capability_executor(runtime),
        step_handler_registry=registry,
    )

    result = engine.run({})

    assert result.status == "COMPLETED"
    assert result.output == {"ok": True}
    assert result.state["custom_step_executed"] is True


def test_unknown_step_type_fails_during_definition_validation():
    definition = minimal_definition([
        {"id": "unknown", "type": "not_registered"},
    ])
    runtime = MockRuntime()
    with pytest.raises(WorkflowDefinitionError, match="Unsupported step type"):
        WorkflowEngine(definition, runtime)


def test_step_specific_validation_is_delegated_to_handler():
    registry = StepHandlerRegistry()
    registry.register("custom", CustomStepHandler())
    definition = minimal_definition([{"id": "custom_step", "type": "custom"}])
    runtime = MockRuntime()
    with pytest.raises(WorkflowDefinitionError, match="custom step requires next"):
        WorkflowEngine(definition, runtime, step_handler_registry=registry)


def test_duplicate_step_ids_are_rejected():
    definition = minimal_definition([
        {"id": "same", "type": "terminal"},
        {"id": "same", "type": "terminal"},
    ])
    runtime = MockRuntime()
    with pytest.raises(WorkflowDefinitionError, match="Duplicate step id"):
        WorkflowEngine(definition, runtime)
