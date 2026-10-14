from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"YAML root in {path} must be an object")
    return value


def load_workflow(path: str | Path) -> dict[str, Any]:
    definition = load_yaml(path)
    if "workflow" not in definition or not isinstance(definition["workflow"], dict):
        raise ValueError(f"Workflow file {path} must contain a 'workflow' object")
    return definition


def load_profiles(path: str | Path) -> dict[str, Any]:
    """Load profiles and resolve reusable `includes` composition.

    Included profile properties are merged in declaration order. A property
    declared later with the same ID overrides the earlier definition while
    retaining its position. Cycles and unknown profile references are errors.
    """
    data = load_yaml(path)
    raw = data.get("property_profiles", data.get("profiles", data))
    if not isinstance(raw, dict):
        raise ValueError("Profile file must contain a property_profiles mapping")

    resolved: dict[str, Any] = {}
    resolving: set[str] = set()

    def resolve_profile(profile_id: str) -> dict[str, Any]:
        if profile_id in resolved:
            return resolved[profile_id]
        if profile_id in resolving:
            raise ValueError(f"Circular profile inclusion detected at '{profile_id}'")
        if profile_id not in raw:
            raise ValueError(f"Unknown included property profile '{profile_id}'")
        resolving.add(profile_id)
        source = raw[profile_id] or {}
        merged: dict[str, Any] = {
            key: value for key, value in source.items()
            if key not in {"includes", "extends", "properties"}
        }
        property_items: list[dict[str, Any]] = []
        property_index: dict[str, int] = {}
        includes = source.get("includes", [])
        if source.get("extends"):
            includes = [*includes, source["extends"]] if isinstance(includes, list) else [includes, source["extends"]]
        if isinstance(includes, str):
            includes = [includes]
        for include_id in includes:
            included = resolve_profile(include_id)
            for prop in included.get("properties", []):
                prop_id = prop if isinstance(prop, str) else prop["id"]
                if prop_id in property_index:
                    property_items[property_index[prop_id]] = prop
                else:
                    property_index[prop_id] = len(property_items)
                    property_items.append(prop)
        for prop in source.get("properties", []) or []:
            prop_id = prop if isinstance(prop, str) else prop["id"]
            if prop_id in property_index:
                property_items[property_index[prop_id]] = prop
            else:
                property_index[prop_id] = len(property_items)
                property_items.append(prop)
        merged.setdefault("id", profile_id)
        merged.setdefault("name", profile_id.replace("_", " ").title())
        merged["properties"] = property_items
        resolving.remove(profile_id)
        resolved[profile_id] = merged
        return merged

    for key in raw:
        resolve_profile(key)
    return resolved
