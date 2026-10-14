from __future__ import annotations

import os
from typing import Any

from workflow_engine.runtime import RuntimeAdapter


class LangChainModelClient:
    def __init__(self, model: Any):
        self.model = model

    def complete(self, prompt: str) -> str:
        response = self.model.invoke(prompt)
        content = getattr(response, "content", response)
        if isinstance(content, list):
            content = "".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in content
            )
        return str(content)


class LangChainRuntime(RuntimeAdapter):
    """LangChain model adapter; shared capabilities live outside this class."""

    runtime_name = "langchain"

    def __init__(self, model: Any | None = None, human_input_handler=None):
        if model is None:
            try:
                from langchain_openai import ChatOpenAI
            except ImportError as exc:
                raise RuntimeError(
                    "LangChain runtime requires langchain-openai. "
                    "Run: pip install -r requirements-langchain.txt"
                ) from exc
            kwargs: dict[str, Any] = {
                "model": os.getenv("LANGCHAIN_MODEL", "gpt-4o-mini"),
                "temperature": 0,
            }
            if os.getenv("LANGCHAIN_BASE_URL"):
                kwargs["base_url"] = os.environ["LANGCHAIN_BASE_URL"]
            model = ChatOpenAI(**kwargs)
        self._model_client = LangChainModelClient(model)
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
