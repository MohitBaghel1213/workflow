from __future__ import annotations

from typing import Any

from tools import ToolManager
from .capabilities import CapabilityExecutor, CapabilityRegistry
from .capabilities.handlers import (
    ConfirmationClassificationHandler,
    FailureClassificationHandler,
    PropertyExtractionHandler,
    ToolBackedCapability,
    ValidationHandler,
)


class MockChemicalSearchTool:
    """Deterministic example integration; replace with a real data source."""

    def execute(self, inputs: dict[str, Any], context: Any) -> dict[str, Any]:
        query = inputs.get("query", "")
        return {
            "query": query,
            "candidates": [],
            "note": "Mock tool: connect a chemical database or search API here.",
        }


def build_tool_manager() -> ToolManager:
    manager = ToolManager()
    manager.register("chemical_database_search", MockChemicalSearchTool())
    return manager


def build_capability_registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()
    registry.register(
        "property_extraction", PropertyExtractionHandler(),
        metadata={"required_inputs": ["user_prompt", "property_profile"]},
    )
    registry.register(
        "validation", ValidationHandler(),
        metadata={"required_inputs": ["properties", "property_profile"]},
    )
    registry.register(
        "failure_classification", FailureClassificationHandler(),
        metadata={"required_inputs": []},
    )
    registry.register(
        "confirmation_classification", ConfirmationClassificationHandler(),
        metadata={"required_inputs": ["response", "current_properties"]},
    )
    registry.register(
        "chemical_search", ToolBackedCapability("chemical_database_search"),
        metadata={"required_inputs": ["query"]},
    )
    return registry


def build_capability_executor(runtime: Any, tool_manager: ToolManager | None = None) -> CapabilityExecutor:
    return CapabilityExecutor(
        build_capability_registry(),
        services={
            "model_client": runtime.model_client,
            "tool_manager": tool_manager or build_tool_manager(),
        },
    )
