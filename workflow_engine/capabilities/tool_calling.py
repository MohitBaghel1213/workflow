from __future__ import annotations

from typing import Any


class AgentCapability:
    """Generic capability wrapper around the shared ToolCallingAgentRuntime.

    Per-agent behavior is supplied through ExecutionContext.config (normally
    from workflow YAML); this class contains no chemical-specific logic and no
    tool-calling loop.
    """

    def execute(self, inputs: dict[str, Any], context: Any) -> dict[str, Any]:
        tool_manager = context.services.get("tool_manager")
        agent_runtime = context.services.get("agent_runtime")
        if tool_manager is None:
            raise RuntimeError("Agent capability is missing the 'tool_manager' service")
        if agent_runtime is None:
            raise RuntimeError("Agent capability is missing the 'agent_runtime' service")

        config = context.config or {}
        instructions = config.get("instructions")
        tool_ids = config.get("tools") or []
        max_iterations = config.get("max_iterations", 8)
        if not isinstance(instructions, str) or not instructions.strip():
            raise ValueError("Agent capability config requires non-empty 'instructions'")
        if not isinstance(tool_ids, list) or not all(isinstance(item, str) for item in tool_ids):
            raise ValueError("Agent capability config 'tools' must be a list of tool IDs")

        return agent_runtime.run(
            instructions=instructions,
            inputs=inputs,
            tool_manager=tool_manager,
            tool_ids=tool_ids,
            context=context,
            max_iterations=max_iterations,
        )
