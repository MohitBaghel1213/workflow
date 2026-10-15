from __future__ import annotations

import json
from typing import Any, Protocol


class ToolCallingModel(Protocol):
    """Provider-neutral contract for one model decision in an agent loop."""

    def next_action(self, *, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        """Return either {type: tool_call, name, arguments} or {type: final, ...}."""
        ...


class ToolCallingAgentRuntime:
    """Reusable tool-calling loop shared by all agentic capabilities.

    The runtime owns the loop; capabilities only provide instructions, inputs,
    the permitted tool IDs, and execution limits. Provider-specific adapters can
    implement the ToolCallingModel contract without changing capabilities.
    """

    def __init__(self, model: ToolCallingModel):
        self.model = model

    def run(
        self,
        *,
        instructions: str,
        inputs: dict[str, Any],
        tool_manager: Any,
        tool_ids: list[str],
        context: Any,
        max_iterations: int = 8,
    ) -> dict[str, Any]:
        if not tool_ids:
            raise ValueError("Agent configuration must allow at least one tool")
        if max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")

        # Tool definitions are pulled from the central registry at runtime.
        tool_definitions = tool_manager.definitions(tool_ids)
        print("\n[agent] Tool definitions loaded from ToolManager:")
        for definition in tool_definitions:
            print(f"  - {definition['name']}: {definition['description']}")

        messages: list[dict[str, Any]] = [{
            "role": "user",
            "content": f"{instructions.strip()}\n\nInputs: {json.dumps(inputs, sort_keys=True)}",
        }]
        trace: list[dict[str, Any]] = []
        allowed_tools = set(tool_ids)

        for _iteration in range(1, max_iterations + 1):
            action = self.model.next_action(messages=messages, tools=tool_definitions)
            action_type = action.get("type")
            if action_type == "final":
                print("[agent] Model returned a final answer.")
                result = {key: value for key, value in action.items() if key != "type"}
                if "content" in result and "summary" not in result:
                    result["summary"] = result.pop("content")
                result["tool_trace"] = trace
                result["model_mode"] = getattr(self.model, "mode", type(self.model).__name__)
                return result

            if action_type != "tool_call":
                raise ValueError(f"Unsupported model action: {action!r}")

            tool_name = action.get("name")
            arguments = action.get("arguments") or {}
            if tool_name not in allowed_tools:
                raise ValueError(f"Model requested tool outside capability allowlist: {tool_name}")
            if not isinstance(arguments, dict):
                raise ValueError(f"Tool arguments for '{tool_name}' must be an object")

            print(f"[agent] Model requested tool: {tool_name}({json.dumps(arguments)})")
            tool_result = tool_manager.execute(tool_name, arguments, context)
            print(f"[tool:{tool_name}] {json.dumps(tool_result, ensure_ascii=False)}")
            trace.append({"tool": tool_name, "arguments": arguments, "result": tool_result})
            messages.append({"role": "assistant", "tool_call": {"name": tool_name, "arguments": arguments}})
            messages.append({"role": "tool", "name": tool_name, "content": json.dumps(tool_result)})

        raise RuntimeError(f"Agent exceeded max_iterations={max_iterations} without a final answer")
