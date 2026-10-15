from __future__ import annotations

import json
from typing import Any


class MockToolCallingModel:
    """Generic deterministic tool-calling stand-in for demos and tests.

    It calls the available tools in order, synthesizes arguments from their JSON
    schemas and prior tool results, then returns a final response. It does not
    simulate intelligent reasoning; use a provider adapter for real model choice.
    """

    mode = "scripted-mock-tool-calling-model"

    @staticmethod
    def _input_payload(messages: list[dict[str, Any]]) -> dict[str, Any]:
        user_message = next(m["content"] for m in messages if m.get("role") == "user")
        marker = "Inputs: "
        if marker not in user_message:
            return {}
        return json.loads(user_message.split(marker, 1)[1])

    @staticmethod
    def _tool_results(messages: list[dict[str, Any]]) -> list[tuple[str, Any]]:
        return [
            (message["name"], json.loads(message["content"]))
            for message in messages
            if message.get("role") == "tool"
        ]

    def next_action(self, *, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        payload = self._input_payload(messages)
        results = self._tool_results(messages)
        called = {name for name, _ in results}
        next_tool = next((tool for tool in tools if tool["name"] not in called), None)

        if next_tool is not None:
            schema = next_tool.get("input_schema") or {}
            properties = schema.get("properties") or {}
            previous_result = results[-1][1] if results else {}
            arguments: dict[str, Any] = {}
            for key in schema.get("required", list(properties)):
                if key in {"requirements", "query", "search_query"}:
                    value = payload.get("properties", payload)
                    arguments[key] = json.dumps(value, sort_keys=True) if isinstance(value, dict) else str(value)
                elif key in {"candidates", "items", "results"}:
                    value = previous_result.get("candidates") or previous_result.get("ranked_candidates") or []
                    arguments[key] = value
                elif key in payload:
                    arguments[key] = payload[key]
                elif key in properties and properties[key].get("type") == "string":
                    arguments[key] = str(payload.get(key, "demo"))
                elif key in properties and properties[key].get("type") == "array":
                    arguments[key] = []
                elif key in properties and properties[key].get("type") == "object":
                    arguments[key] = {}
                else:
                    arguments[key] = payload.get(key)
            return {"type": "tool_call", "name": next_tool["name"], "arguments": arguments}

        last_result = results[-1][1] if results else {}
        candidates = last_result.get("ranked_candidates") or last_result.get("candidates") or []
        return {
            "type": "final",
            "content": "Mock agent run completed. Tool outputs are illustrative and must be validated before real-world use.",
            "candidates": candidates,
            "last_tool_result": last_result,
        }
