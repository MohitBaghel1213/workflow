from __future__ import annotations

from typing import Any

from tools import ToolManager
from .capabilities import CapabilityExecutor, CapabilityRegistry
from .capabilities.chemical import ChemicalWorkflowCapability
from .capabilities.handlers import (
    ConfirmationClassificationHandler,
    FailureClassificationHandler,
    PropertyExtractionHandler,
    ToolBackedCapability,
    ValidationHandler,
)
from .capabilities.tool_calling import AgentCapability
from .agent_runtime import ToolCallingAgentRuntime
from runtimes.mock_tool_calling_model import MockToolCallingModel


class MockChemicalDatabaseSearchTool:
    """Hardcoded example data; replace with a validated materials source."""
    def execute(self, inputs: dict[str, Any], context: Any) -> dict[str, Any]:
        requirements = inputs.get("requirements") or inputs.get("query", "")
        print("[tool implementation] Searching mock chemical/material database...")
        candidates = [
            {"id": "MAT-101", "name": "Candidate Alpha", "family": "illustrative polymer", "notes": "Mock candidate; compatibility testing required."},
            {"id": "MAT-202", "name": "Candidate Beta", "family": "illustrative composite", "notes": "Mock candidate; verify processing and safety requirements."},
        ] if requirements else []
        return {"query": requirements, "candidates": candidates, "source": "HARDCODED_DEMO_DATA",
                "warning": "Not a real materials database."}


class MockCandidateComparisonTool:
    def execute(self, inputs: dict[str, Any], context: Any) -> dict[str, Any]:
        candidates = inputs.get("candidates", [])
        print(f"[tool implementation] Comparing {len(candidates)} mock candidates...")
        ranked = []
        for candidate, score in zip(candidates, (0.86, 0.73)):
            ranked.append({**candidate, "illustrative_match_score": score,
                           "score_warning": "Demo score only; not validated equivalence."})
        ranked.sort(key=lambda item: item["illustrative_match_score"], reverse=True)
        return {"ranked_candidates": ranked, "candidates": ranked, "source": "HARDCODED_DEMO_DATA"}


def build_tool_manager() -> ToolManager:
    manager = ToolManager()
    manager.register(
        "chemical_database_search", MockChemicalDatabaseSearchTool(),
        description="Search the hardcoded demo materials database for candidate alternatives.",
        input_schema={"type": "object", "properties": {"requirements": {"type": "string"}}, "required": ["requirements"]},
    )
    manager.register(
        "compare_chemical_candidates", MockCandidateComparisonTool(),
        description="Compare candidate materials and return illustrative match scores.",
        input_schema={"type": "object", "properties": {"candidates": {"type": "array", "items": {"type": "object"}}}, "required": ["candidates"]},
    )
    return manager


def build_capability_registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()
    # Retain generic example capabilities for extension/tests, alongside domain capabilities.
    registry.register("property_extraction", PropertyExtractionHandler(), metadata={"required_inputs": ["user_prompt", "property_profile"]})
    registry.register("validation", ValidationHandler(), metadata={"required_inputs": ["properties", "property_profile"]})
    registry.register("failure_classification", FailureClassificationHandler(), metadata={"required_inputs": []})
    registry.register("confirmation_classification", ConfirmationClassificationHandler(), metadata={"required_inputs": ["response", "current_properties"]})
    registry.register("chemical_search", ToolBackedCapability("chemical_database_search"), metadata={"required_inputs": []})
    registry.register("agent", AgentCapability(), metadata={"required_inputs": []})

    operations = [
        "extract_contract_slots", "validate_contract_slots", "classify_user_confirmation",
        "merge_resolved_properties", "build_application_context", "formulate_ashby_problem",
        "classify_ashby_confirmation", "generate_material_equation", "derive_baseline_property_request",
        "search_candidate_materials", "derive_candidate_property_request", "construct_alternatives",
        "screen_alternatives", "rank_alternatives", "classify_failure",
        "resolve_from_knowledge_graph", "resolve_from_web", "resolve_with_llm",
        "merge_resolution_result", "validate_resolution_result",
    ]
    for operation in operations:
        registry.register(operation, ChemicalWorkflowCapability(operation), metadata={"required_inputs": []})
    return registry


def build_capability_executor(
    runtime: Any,
    tool_manager: ToolManager | None = None,
    agent_runtime: Any | None = None,
) -> CapabilityExecutor:
    manager = tool_manager or build_tool_manager()
    if agent_runtime is None:
        agent_runtime = getattr(runtime, "agent_runtime", None)
    if agent_runtime is None:
        model = getattr(runtime, "tool_calling_model", None) or MockToolCallingModel()
        agent_runtime = ToolCallingAgentRuntime(model)
    services = {
        "model_client": runtime.model_client,
        "tool_manager": manager,
        "agent_runtime": agent_runtime,
    }
    return CapabilityExecutor(build_capability_registry(), services=services)
