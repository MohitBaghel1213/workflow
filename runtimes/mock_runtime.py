from __future__ import annotations

import re
from typing import Any

from workflow_engine.runtime import Runtime


class MockRuntime(Runtime):
    """
    Fully runnable reference runtime.

    It demonstrates the runtime contract without requiring an LLM provider.
    Replace the capability implementations with LangChain, Claude Agent SDK,
    Microsoft Agent Framework, or another framework without changing
    workflow.yaml.
    """

    def invoke_capability(
        self,
        capability: str,
        inputs: dict[str, Any],
        context: dict[str, Any],
    ) -> Any:

        if capability == "property_extraction":
            return self._extract(inputs["user_prompt"], inputs.get("existing_properties") or {})

        if capability == "validation":
            return self._validate(
                inputs["properties"],
                inputs["schema"],
            )

        if capability == "failure_classification":
            return "SYSTEM_ERROR"

        if capability == "confirmation_classification":
            return self._classify_confirmation(
                inputs["response"],
                inputs["current_properties"],
            )

        raise ValueError(f"Unsupported capability: {capability}")

    def request_human_input(self, prompt: str, context: dict[str, Any]) -> str:
        print("\n" + "=" * 72)
        print("HUMAN INPUT REQUIRED")
        print("=" * 72)
        print(prompt)
        print("=" * 72)
        return input("Your response: ").strip()

    @staticmethod
    def _extract(prompt: str, existing: dict[str, Any]) -> dict[str, Any]:
        properties = dict(existing)

        # Demo syntax:
        # property_a=foo property_b=bar property_c=baz property_d=qux property_e=xyz
        for name in ("property_a", "property_b", "property_c", "property_d", "property_e"):
            match = re.search(
                rf"\b{name}\s*=\s*([^\s,;]+)",
                prompt,
                flags=re.IGNORECASE,
            )
            if match:
                properties[name] = match.group(1)

        return properties

    @staticmethod
    def _validate(properties: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        required = schema.get("required", [])
        missing = [
            name for name in required
            if properties.get(name) in (None, "")
        ]

        errors = [
            {
                "property": name,
                "code": "REQUIRED_PROPERTY_MISSING",
                "message": f"{name} is required",
            }
            for name in missing
        ]

        return {
            "validation_status": "VALID" if not missing else "INVALID",
            "missing_properties": missing,
            "validation_errors": errors,
        }

    @staticmethod
    def _classify_confirmation(
        response: str,
        current: dict[str, Any],
    ) -> dict[str, Any]:
        normalized = response.strip().lower()

        if normalized in {
            "yes",
            "y",
            "yes, correct",
            "correct",
            "confirmed",
            "confirm",
            "looks good",
            "everything is correct",
        }:
            return {
                "decision": "CONFIRMED",
                "corrections": {},
            }

        corrections = {}
        for name in current:
            match = re.search(
                rf"\b{name}\s*(?:is|=|should be)\s*([^\s,;.]+)",
                response,
                flags=re.IGNORECASE,
            )
            if match:
                corrections[name] = match.group(1)

        if corrections:
            return {
                "decision": "CORRECTION_REQUIRED",
                "corrections": corrections,
            }

        return {
            "decision": "UNCLEAR",
            "corrections": {},
        }
