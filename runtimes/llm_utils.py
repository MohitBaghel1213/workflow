from __future__ import annotations

import json
import re
from typing import Any
import os

from langchain_openai import ChatOpenAI
from langchain.chat_models import init_chat_model


REQUIRED_FIELDS = (
    "property_a",
    "property_b",
    "property_c",
    "property_d",
    "property_e",
)


def validation_result(properties: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    required = schema.get("required", list(REQUIRED_FIELDS))
    missing = [name for name in required if properties.get(name) in (None, "")]
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


def parse_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object from an LLM response, tolerating markdown fences."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end <= start:
            raise ValueError(f"LLM did not return a JSON object: {text!r}")
        value = json.loads(cleaned[start : end + 1])

    if not isinstance(value, dict):
        raise ValueError("LLM response must be a JSON object")
    return value


def extraction_prompt(user_prompt: str, existing: dict[str, Any]) -> str:
    return f"""
Extract the five required properties from the user's text.

Required properties:
- property_a
- property_b
- property_c
- property_d
- property_e

Existing properties may already be known. Preserve them unless the user's new
text explicitly corrects them.

Return ONLY a JSON object with these keys when known. Do not invent values.
Example: {{"property_a":"A","property_b":"B"}}

Existing properties:
{json.dumps(existing, ensure_ascii=False)}

User text:
{user_prompt}
""".strip()


def confirmation_prompt(response: str, current: dict[str, Any]) -> str:
    return f"""
Classify the user's response to a confirmation request.

Current extracted properties:
{json.dumps(current, ensure_ascii=False)}

User response:
{response}

Return ONLY JSON in this shape:
{{
  "decision": "CONFIRMED" | "CORRECTION_REQUIRED" | "UNCLEAR",
  "corrections": {{}}
}}

Use CONFIRMED only when the user clearly accepts the values.
Use CORRECTION_REQUIRED when the user provides one or more corrections.
Put corrected property values in the corrections object.
Use UNCLEAR when intent cannot be determined.
Do not invent corrections.
""".strip()


def failure_classification(error: dict[str, Any] | None, validation_errors: list[Any]) -> str:
    """Conservative deterministic failure classification for the reference project."""
    if validation_errors:
        return "MISSING_INPUT"
    if error and error.get("type") in {"TimeoutError", "ConnectionError"}:
        return "TRANSIENT_ERROR"
    return "SYSTEM_ERROR"

# model = init_chat_model("ollama:qwen3:1.7b")
model = ChatOpenAI(model="apodex/apodex-1.1-mini:free", base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"])