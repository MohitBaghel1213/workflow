from __future__ import annotations

from typing import Any

from .contracts import ExecutionContext
from runtimes.llm_utils import (
    confirmation_prompt,
    extraction_prompt,
    failure_classification,
    parse_json_object,
    validation_result,
)


class PropertyExtractionHandler:
    def execute(self, inputs: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        client = context.services.get("model_client")
        if client is None:
            raise RuntimeError("No model_client service is configured")
        prompt = extraction_prompt(
            inputs["user_prompt"],
            inputs.get("existing_properties") or {},
            inputs["property_profile"],
        )
        result = parse_json_object(client.complete(prompt))
        allowed = {
            item if isinstance(item, str) else item["id"]
            for item in inputs["property_profile"].get("properties", [])
        }
        # Preserve existing values and only accept keys defined by the profile.
        merged = dict(inputs.get("existing_properties") or {})
        merged.update({key: value for key, value in result.items() if key in allowed})
        return merged


class ValidationHandler:
    def execute(self, inputs: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        return validation_result(inputs["properties"], inputs["property_profile"])


class FailureClassificationHandler:
    def execute(self, inputs: dict[str, Any], context: ExecutionContext) -> str:
        return failure_classification(
            inputs.get("error"), inputs.get("validation_errors") or []
        )


class ConfirmationClassificationHandler:
    def execute(self, inputs: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        client = context.services.get("model_client")
        if client is None:
            raise RuntimeError("No model_client service is configured")
        result = parse_json_object(client.complete(
            confirmation_prompt(inputs["response"], inputs["current_properties"])
        ))
        decision = result.get("decision", "UNCLEAR")
        if decision not in {"CONFIRMED", "CORRECTION_REQUIRED", "UNCLEAR"}:
            decision = "UNCLEAR"
        corrections = result.get("corrections") or {}
        if not isinstance(corrections, dict):
            corrections = {}
        return {"decision": decision, "corrections": corrections}


class ToolBackedCapability:
    """Example adapter for capabilities that delegate to a registered tool."""

    def __init__(self, tool_id: str):
        self.tool_id = tool_id

    def execute(self, inputs: dict[str, Any], context: ExecutionContext) -> Any:
        manager = context.services.get("tool_manager")
        if manager is None:
            raise RuntimeError("No tool_manager service is configured")
        return manager.execute(self.tool_id, inputs, context)
