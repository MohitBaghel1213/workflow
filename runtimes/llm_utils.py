from __future__ import annotations

import json
import re
from typing import Any


def property_specs(profile: dict[str, Any] | None) -> list[dict[str, Any]]:
    profile = profile or {}
    specs = profile.get("properties", [])
    normalized = []
    for item in specs:
        if isinstance(item, str):
            normalized.append({"id": item, "label": item, "type": "string", "required": True})
        else:
            normalized.append({
                "id": item["id"],
                "label": item.get("label", item["id"]),
                "type": item.get("type", "string"),
                "required": item.get("required", True),
                **({"description": item["description"]} if item.get("description") else {}),
            })
    return normalized


def required_property_ids(profile: dict[str, Any] | None) -> list[str]:
    return [spec["id"] for spec in property_specs(profile) if spec.get("required", True)]


def validation_result(properties: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    specs = property_specs(profile)
    required = [spec["id"] for spec in specs if spec.get("required", True)]
    missing = [name for name in required if properties.get(name) in (None, "")]
    errors = [
        {
            "property": name,
            "code": "REQUIRED_PROPERTY_MISSING",
            "message": f"{name} is required",
        }
        for name in missing
    ]
    known = {spec["id"] for spec in specs}
    unknown = sorted(set(properties) - known)
    errors.extend({
        "property": name,
        "code": "UNKNOWN_PROPERTY",
        "message": f"{name} is not defined in the selected property profile",
    } for name in unknown)
    invalid_types = []
    for spec in specs:
        value = properties.get(spec["id"])
        if value in (None, ""):
            continue
        expected = spec.get("type", "string")
        if expected == "string" and not isinstance(value, str):
            invalid_types.append(spec["id"])
        elif expected == "number" and not isinstance(value, (int, float)):
            invalid_types.append(spec["id"])
        elif expected == "integer" and not isinstance(value, int):
            invalid_types.append(spec["id"])
        elif expected == "boolean" and not isinstance(value, bool):
            invalid_types.append(spec["id"])
    errors.extend({
        "property": name,
        "code": "INVALID_TYPE",
        "message": f"{name} has an invalid type",
    } for name in invalid_types)
    valid = not missing and not unknown and not invalid_types
    return {
        "validation_status": "VALID" if valid else "INVALID",
        "missing_properties": missing,
        "validation_errors": errors,
    }


def parse_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object from model output, tolerating markdown fences."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ValueError(f"Model did not return a JSON object: {text!r}")
        value = json.loads(cleaned[start:end + 1])
    if not isinstance(value, dict):
        raise ValueError("Model response must be a JSON object")
    return value


def extraction_prompt(user_prompt: str, existing: dict[str, Any], profile: dict[str, Any]) -> str:
    payload = {
        "user_prompt": user_prompt,
        "existing_properties": existing,
        "property_profile": profile,
    }
    return """TASK:PROPERTY_EXTRACTION
Extract values for the properties declared in property_profile.properties.
Return only a JSON object mapping property IDs to known values. Do not invent values.
Preserve existing_properties unless the user text explicitly corrects a value.
Only return property IDs defined in the profile.
INPUT_JSON:
""" + json.dumps(payload, ensure_ascii=False)


def confirmation_prompt(response: str, current: dict[str, Any]) -> str:
    payload = {"response": response, "current_properties": current}
    return """TASK:CONFIRMATION_CLASSIFICATION
Classify the user's response to the confirmation request.
Return only JSON with decision (CONFIRMED, CORRECTION_REQUIRED, or UNCLEAR) and corrections (object).
Use CONFIRMED only when the user clearly accepts all values. Use CORRECTION_REQUIRED
when the user specifies corrections; corrections must contain only changed property IDs.
Use UNCLEAR if intent cannot be determined. Do not invent corrections.
INPUT_JSON:
""" + json.dumps(payload, ensure_ascii=False)


def failure_classification(error: dict[str, Any] | None, validation_errors: list[Any]) -> str:
    if validation_errors:
        return "MISSING_INPUT"
    if error and error.get("type") in {"TimeoutError", "ConnectionError", "ProviderOverloadedError"}:
        return "TRANSIENT_ERROR"
    return "SYSTEM_ERROR"
