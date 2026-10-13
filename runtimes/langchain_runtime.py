from __future__ import annotations

import os
from typing import Any

from workflow_engine.runtime import Runtime
from .llm_utils import (
    confirmation_prompt,
    extraction_prompt,
    failure_classification,
    parse_json_object,
    validation_result,
    model
)


class LangChainRuntime(Runtime):
    """Runnable LangChain runtime for the framework-neutral workflow.

    The workflow engine never imports LangChain. This adapter owns the model
    and translates generic capability calls into LangChain model invocations.

    Configuration:
      OPENAI_API_KEY: required by the default OpenAI-compatible client.
      LANGCHAIN_MODEL: defaults to gpt-4o-mini.
      LANGCHAIN_BASE_URL: optional OpenAI-compatible endpoint, useful for
        OpenRouter, Groq, or another compatible provider.
    """

    def __init__(self, model: Any | None = None, human_input_handler=None):
        # if model is None:
        #     try:
        #         from langchain_openai import ChatOpenAI
        #     except ImportError as exc:
        #         raise RuntimeError(
        #             "LangChain runtime requires langchain-openai. "
        #             "Run: pip install -r requirements-langchain.txt"
        #         ) from exc

        #     kwargs: dict[str, Any] = {
        #         "model": os.getenv("LANGCHAIN_MODEL", "gpt-4o-mini"),
        #         "temperature": 0,
        #     }
        #     base_url = os.getenv("LANGCHAIN_BASE_URL")
        #     if base_url:
        #         kwargs["base_url"] = base_url
        #     model = ChatOpenAI(**kwargs)

        self.model = model
        self.human_input_handler = human_input_handler or self._console_input

    def invoke_capability(self, capability: str, inputs: dict[str, Any], context: dict[str, Any]) -> Any:
        if capability == "property_extraction":
            text = self._invoke_text(extraction_prompt(inputs["user_prompt"], inputs.get("existing_properties") or {}))
            return parse_json_object(text)

        if capability == "validation":
            return validation_result(inputs["properties"], inputs["schema"])

        if capability == "failure_classification":
            return failure_classification(inputs.get("error"), inputs.get("validation_errors") or [])

        if capability == "confirmation_classification":
            text = self._invoke_text(
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

    def _invoke_text(self, prompt: str) -> str:
        response = self.model.invoke(prompt)
        content = getattr(response, "content", response)
        if isinstance(content, list):
            content = "".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in content
            )
        return str(content)

    @staticmethod
    def _console_input(prompt: str, context: dict[str, Any]) -> str:
        print("\n" + "=" * 72)
        print("HUMAN INPUT REQUIRED")
        print("=" * 72)
        print(prompt)
        print("=" * 72)
        return input("Your response: ").strip()
