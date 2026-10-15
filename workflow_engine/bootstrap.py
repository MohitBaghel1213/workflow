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
from .capabilities.tool_calling import AgentCapability
from .agent_runtime import ToolCallingAgentRuntime
from runtimes.mock_tool_calling_model import MockToolCallingModel


class MockChemicalDatabaseSearchTool:
    """Hardcoded sample results; replace with a vetted chemical data source."""
    def execute(self, inputs: dict[str, Any], context: Any) -> dict[str, Any]:
        requirements = inputs.get("requirements", "")
        query = inputs.get("query", "chemical alternative search")
        print("[tool implementation] Searching mock chemical database...")
        candidates = [] if not requirements else [
            {"id": "ALT-101", "name": "Candidate Alpha", "chemical_family": "illustrative solvent", "notes": "Mock candidate; requires compatibility testing."},
            {"id": "ALT-202", "name": "Candidate Beta", "chemical_family": "illustrative solvent blend", "notes": "Mock candidate; verify process and safety requirements."},
        ]
        return {
            "query": query,
            "requirements_received": requirements or query,
            "candidates": candidates,
            "source": "HARDCODED_DEMO_DATA",
        }


class MockCandidateComparisonTool:
    def execute(self, inputs: dict[str, Any], context: Any) -> dict[str, Any]:
        candidates = inputs.get("candidates", [])
        print(f"[tool implementation] Comparing {len(candidates)} mock candidates...")
        ranked = []
        for candidate, score in zip(candidates, (0.86, 0.73)):
            ranked.append({**candidate, "illustrative_match_score": score,
                           "score_warning": "Demo score only; not validated chemical equivalence."})
        ranked.sort(key=lambda item: item["illustrative_match_score"], reverse=True)
        return {"ranked_candidates": ranked, "source": "HARDCODED_DEMO_DATA"}


def build_tool_manager() -> ToolManager:
    manager = ToolManager()
    manager.register(
        "chemical_database_search", MockChemicalDatabaseSearchTool(),
        description="Search a mock chemical database for candidate alternatives.",
        input_schema={"type": "object", "properties": {"requirements": {"type": "string"}}, "required": ["requirements"]},
    )
    manager.register(
        "compare_chemical_candidates", MockCandidateComparisonTool(),
        description="Compare and rank candidate alternatives against requirements (mock scoring).",
        input_schema={"type": "object", "properties": {"candidates": {"type": "array", "items": {"type": "object"}}}, "required": ["candidates"]},
    )
    return manager


def build_capability_registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()
    registry.register("property_extraction", PropertyExtractionHandler(), metadata={"required_inputs": ["user_prompt", "property_profile"]})
    registry.register("validation", ValidationHandler(), metadata={"required_inputs": ["properties", "property_profile"]})
    registry.register("failure_classification", FailureClassificationHandler(), metadata={"required_inputs": []})
    registry.register("confirmation_classification", ConfirmationClassificationHandler(), metadata={"required_inputs": ["response", "current_properties"]})
    registry.register("chemical_search", ToolBackedCapability("chemical_database_search"), metadata={"required_inputs": ["query"]})
    # One generic agent implementation is reused by every YAML-defined agent capability.
    registry.register("agent", AgentCapability(), metadata={"required_inputs": []})
    return registry


def build_capability_executor(
    runtime: Any,
    tool_manager: ToolManager | None = None,
    agent_runtime: Any | None = None,
) -> CapabilityExecutor:
    manager = tool_manager or build_tool_manager()
    # Runtime adapters may supply a fully configured agent runtime. Otherwise,
    # adapt their tool-calling model; the scripted model keeps the demo runnable
    # with adapters that only implement text completion.
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
