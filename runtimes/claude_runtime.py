from __future__ import annotations

import asyncio
import os
from typing import Any

from workflow_engine.runtime import Runtime
from .llm_utils import (
    confirmation_prompt,
    extraction_prompt,
    failure_classification,
    parse_json_object,
    validation_result,
)


class ClaudeRuntime(Runtime):
    """Runnable Claude Agent SDK runtime for the same workflow YAML.

    The generic engine remains synchronous for simplicity. This adapter bridges
    the Claude Agent SDK's async `query()` interface to the synchronous
    Runtime contract.

    Configuration:
      ANTHROPIC_API_KEY: required by Claude Agent SDK.
      ANTHROPIC_MODEL: defaults to claude-sonnet-5-5.
    """

    def __init__(self, model: str | None = None, human_input_handler=None):
        try:
            from claude_agent_sdk import query
        except ImportError as exc:
            raise RuntimeError(
                "Claude runtime requires claude-agent-sdk. "
                "Run: pip install -r requirements-claude.txt"
            ) from exc

        self._query = query
        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
        self.human_input_handler = human_input_handler or self._console_input

    def invoke_capability(self, capability: str, inputs: dict[str, Any], context: dict[str, Any]) -> Any:
        if capability == "property_extraction":
            text = self._invoke_agent(
                extraction_prompt(inputs["user_prompt"], inputs.get("existing_properties") or {})
            )
            return parse_json_object(text)

        if capability == "validation":
            return validation_result(inputs["properties"], inputs["schema"])

        if capability == "failure_classification":
            return failure_classification(inputs.get("error"), inputs.get("validation_errors") or [])

        if capability == "confirmation_classification":
            text = self._invoke_agent(
                confirmation_prompt(inputs["response"], inputs["current_properties"])
            )
            result = parse_json_object(text)
            return {
                "decision": result.get("decision", "UNCLEAR"),
                "corrections": result.get("corrections") or {},
            }

        raise ValueError(f"Unsupported capability: {capability}")

    def request_human_input(self, prompt: str, context: dict[str, Any]) -> str:
        return self.human_input_handler(prompt, context)

    def _invoke_agent(self, prompt: str) -> str:
        return asyncio.run(self._invoke_agent_async(prompt))

    async def _invoke_agent_async(self, prompt: str) -> str:
        try:
            from claude_agent_sdk import AssistantMessage, TextBlock, ClaudeAgentOptions
        except ImportError as exc:
            raise RuntimeError("claude-agent-sdk is not installed") from exc

        texts: list[str] = []
        async for message in self._query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                model=self.model,
                allowed_tools=[],
                max_turns=1,
            ),
        ):
            if isinstance(message, AssistantMessage):
                texts.extend(
                    block.text
                    for block in message.content
                    if isinstance(block, TextBlock)
                )

        if not texts:
            raise RuntimeError("Claude Agent SDK returned no text content")
        return "".join(texts)

    @staticmethod
    def _console_input(prompt: str, context: dict[str, Any]) -> str:
        print("\n" + "=" * 72)
        print("HUMAN INPUT REQUIRED")
        print("=" * 72)
        print(prompt)
        print("=" * 72)
        return input("Your response: ").strip()
