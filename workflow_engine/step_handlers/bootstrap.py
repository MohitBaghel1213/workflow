from __future__ import annotations

from .handlers import (
    CapabilityStepHandler,
    ConditionStepHandler,
    HumanInputStepHandler,
    RetryStepHandler,
    StateUpdateStepHandler,
    SubworkflowStepHandler,
    TerminalStepHandler,
)
from .registry import StepHandlerRegistry


def build_step_handler_registry() -> StepHandlerRegistry:
    """Build the default registry. Add new step types here, not in WorkflowEngine."""
    registry = StepHandlerRegistry()
    registry.register("capability", CapabilityStepHandler())
    registry.register("condition", ConditionStepHandler())
    registry.register("human_input", HumanInputStepHandler())
    registry.register("state_update", StateUpdateStepHandler())
    registry.register("retry", RetryStepHandler())
    registry.register("workflow", SubworkflowStepHandler())
    registry.register("terminal", TerminalStepHandler())
    return registry
