from __future__ import annotations

import asyncio
import os
from typing import Any

from workflow_engine.runtime import RuntimeAdapter


class ClaudeModelClient:
    def __init__(self, query_fn: Any, model: str):
        self.query_fn = query_fn
        self.model = model

    def complete(self, prompt: str) -> str:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self._complete_async(prompt))
        raise RuntimeError(
            "ClaudeModelClient.complete() is synchronous and cannot be called "
            "inside an active event loop. Use an async runtime integration for that host."
        )

    async def _complete_async(self, prompt: str) -> str:
        try:
            from claude_agent_sdk import AssistantMessage, TextBlock, ClaudeAgentOptions
        except ImportError as exc:
            raise RuntimeError("claude-agent-sdk is not installed") from exc
        texts: list[str] = []
        async for message in self.query_fn(
            prompt=prompt,
            options=ClaudeAgentOptions(
                model=self.model,
                allowed_tools=[],
                max_turns=1,
            ),
        ):
            if isinstance(message, AssistantMessage):
                texts.extend(block.text for block in message.content if isinstance(block, TextBlock))
        if not texts:
            raise RuntimeError("Claude Agent SDK returned no text content")
        return "".join(texts)


class ClaudeRuntime(RuntimeAdapter):
    """Claude Agent SDK adapter; it does not own capability dispatch."""

    runtime_name = "claude"

    def __init__(self, model: str | None = None, human_input_handler=None, model_client=None):
        if model_client is None:
            try:
                from claude_agent_sdk import query
            except ImportError as exc:
                raise RuntimeError(
                    "Claude runtime requires claude-agent-sdk. "
                    "Run: pip install -r requirements-claude.txt"
                ) from exc
            model_client = ClaudeModelClient(
                query, model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
            )
        self._model_client = model_client
        self.human_input_handler = human_input_handler or self._console_input

    @property
    def model_client(self):
        return self._model_client

    def request_human_input(self, prompt: str, context: dict[str, Any]) -> str:
        return self.human_input_handler(prompt, context)

    @staticmethod
    def _console_input(prompt: str, context: dict[str, Any]) -> str:
        print("\n" + "=" * 72 + "\nHUMAN INPUT REQUIRED\n" + "=" * 72)
        print(prompt)
        return input("Your response: ").strip()
