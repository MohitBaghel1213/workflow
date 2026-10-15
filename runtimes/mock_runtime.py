from __future__ import annotations

import json
import re
from typing import Any

from workflow_engine.runtime import RuntimeAdapter
from .mock_tool_calling_model import MockToolCallingModel


class MockModelClient:
    """Deterministic local model substitute for tests and demos."""

    def complete(self, prompt: str) -> str:
        if "TASK:PROPERTY_EXTRACTION" in prompt:
            payload = self._payload(prompt)
            user_text = payload.get("user_prompt", "")
            properties = dict(payload.get("existing_properties") or {})
            specs = payload.get("property_profile", {}).get("properties", [])
            for spec in specs:
                prop_id = spec if isinstance(spec, str) else spec["id"]
                match = re.search(
                    rf"(?<![\w]){re.escape(prop_id)}\s*(?:=|:|\bis\b)\s*([^\s,;]+)",
                    user_text,
                    flags=re.IGNORECASE,
                )
                if match:
                    properties[prop_id] = match.group(1).strip().strip(".\"'")
            return json.dumps(properties)

        if "TASK:CONFIRMATION_CLASSIFICATION" in prompt:
            payload = self._payload(prompt)
            response = str(payload.get("response", "")).strip()
            current = payload.get("current_properties") or {}
            normalized = response.lower().strip(".! ")
            if normalized in {
                "yes", "y", "yes, correct", "correct", "confirmed", "confirm",
                "looks good", "everything is correct", "all correct", "approved",
            }:
                return json.dumps({"decision": "CONFIRMED", "corrections": {}})
            corrections: dict[str, Any] = {}
            for name in current:
                match = re.search(
                    rf"(?<![\w]){re.escape(name)}\s*(?:=|:|is|should be)\s*([^\s,;]+)",
                    response,
                    flags=re.IGNORECASE,
                )
                if match:
                    corrections[name] = match.group(1).strip().strip(".\"'")
            if corrections:
                return json.dumps({"decision": "CORRECTION_REQUIRED", "corrections": corrections})
            return json.dumps({"decision": "UNCLEAR", "corrections": {}})

        raise ValueError("MockModelClient received an unknown task")

    @staticmethod
    def _payload(prompt: str) -> dict[str, Any]:
        marker = "INPUT_JSON:\n"
        if marker not in prompt:
            raise ValueError("Prompt is missing INPUT_JSON payload")
        return json.loads(prompt.split(marker, 1)[1])


class MockRuntime(RuntimeAdapter):
    runtime_name = "mock"

    def __init__(self, human_input_handler=None, model_client=None):
        self._model_client = model_client or MockModelClient()
        self._tool_calling_model = MockToolCallingModel()
        self.human_input_handler = human_input_handler or self._console_input

    @property
    def model_client(self):
        return self._model_client

    @property
    def tool_calling_model(self):
        return self._tool_calling_model

    def request_human_input(self, prompt: str, context: dict[str, Any]) -> str:
        return self.human_input_handler(prompt, context)

    @staticmethod
    def _console_input(prompt: str, context: dict[str, Any]) -> str:
        print("\n" + "=" * 72)
        print("HUMAN INPUT REQUIRED")
        print("=" * 72)
        print(prompt)
        print("=" * 72)
        return input("Your response: ").strip()



