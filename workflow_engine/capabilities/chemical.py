"""Deterministic, replaceable demo implementations for chemical workflow capabilities.

These handlers make the end-to-end workflow runnable without external APIs.
Replace source lookup and domain-analysis logic with vetted services before production use.
"""
from __future__ import annotations

import re
from typing import Any

from .contracts import ExecutionContext

SLOT_NAMES = (
    "material", "part", "product", "component",
    "functional_requirement", "reason_for_substitution",
)
SLOT_ALIASES = {
    "material": ("material", "current material", "material to replace"),
    "part": ("part",),
    "product": ("product",),
    "component": ("component",),
    "functional_requirement": ("functional_requirement", "functional requirement", "function"),
    "reason_for_substitution": ("reason_for_substitution", "reason for substitution", "substitution reason", "reason"),
}


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return str(value)
    return str(value).strip()


def _has_concrete_value(value: Any) -> bool:
    normalized = _text(value).strip().lower()
    if not normalized:
        return False
    placeholders = ("unknown", "not provided", "reason not provided", "n/a", "na", "none", "null", "not known")
    return not any(normalized == item or normalized.startswith(item + " ") for item in placeholders)


def _find_slot(text: str, aliases: tuple[str, ...]) -> str | None:
    for alias in aliases:
        pattern = rf"(?<![\w]){re.escape(alias)}\s*(?:=|:|\bis\b)\s*(.+?)(?=(?:[,;]|\n)\s*[\w ]+\s*(?:=|:|\bis\b)|$)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip().strip(" .\"'")
            if value:
                return value
    return None


class ChemicalWorkflowCapability:
    """One operation-specific handler; dispatch is done by the capability registry."""
    def __init__(self, operation: str):
        self.operation = operation

    def execute(self, inputs: dict[str, Any], context: ExecutionContext) -> Any:
        method = getattr(self, f"op_{self.operation}", None)
        if method is None:
            raise NotImplementedError(f"Chemical capability operation '{self.operation}' is not implemented")
        return method(inputs, context)

    def op_extract_contract_slots(self, inputs: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        prompt = _text(inputs.get("user_prompt"))
        for file in inputs.get("files") or []:
            if isinstance(file, dict):
                prompt += "\n" + _text(file.get("text") or file.get("content") or file.get("name"))
        values = {}
        for slot, aliases in SLOT_ALIASES.items():
            found = _find_slot(prompt, aliases)
            if found:
                values[slot] = found
        # Accept compact natural-language demo phrasing such as "replace X".
        if "material" not in values:
            match = re.search(
                r"(?:replace|substitute)\s+(?:the\s+)?([A-Za-z][A-Za-z0-9_-]+)|"
                r"alternative\s+(?:of|for)\s+([A-Za-z][A-Za-z0-9_-]+)",
                prompt,
                re.IGNORECASE,
            )
            if match:
                values["material"] = next(group for group in match.groups() if group)
        return values

    def op_validate_contract_slots(self, inputs: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        values = inputs.get("slots") or {}
        all_slots = inputs.get("all_slots") or list(SLOT_NAMES)
        required = inputs.get("required_slots") or ["material"]
        missing = [slot for slot in all_slots if not _has_concrete_value(values.get(slot))]
        missing_required = [slot for slot in required if slot in missing]
        return {"status": "INVALID" if missing_required else "VALID", "missing": missing,
                "missing_required": missing_required, "errors": [f"Required slot '{x}' is missing" for x in missing_required]}

    def op_classify_user_confirmation(self, inputs: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        response = _text(inputs.get("response"))
        normalized = response.lower().strip(" .!\n")
        if normalized in {"accept", "accepted", "yes", "y", "confirm", "confirmed", "approved", "looks good", "correct"}:
            return {"decision": "ACCEPTED", "corrections": {}, "response": response}
        current = inputs.get("current_values") or {}
        corrections: dict[str, Any] = {}
        for slot, aliases in SLOT_ALIASES.items():
            value = _find_slot(response, aliases)
            if value:
                corrections[slot] = value
        if normalized.startswith("edit") or corrections:
            return {"decision": "EDITS_REQUESTED", "corrections": corrections, "response": response}
        return {"decision": "UNCLEAR", "corrections": {}, "response": response}

    def op_merge_resolved_properties(self, inputs: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        base = dict(inputs.get("base_values") or {})
        resolved = inputs.get("resolved_values") or {}
        values = resolved.get("values", resolved) if isinstance(resolved, dict) else {}
        if isinstance(values, dict):
            for key, value in values.items():
                if value not in (None, "", [], {}):
                    base[key] = value
        return base

    def op_build_application_context(self, inputs: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        slots = inputs.get("slots") or {}
        missing = [slot for slot in SLOT_NAMES if not _has_concrete_value(slots.get(slot))]
        if missing:
            raise ValueError(
                "Cannot build application context until all six contract slots are populated. "
                f"Missing slots: {', '.join(missing)}"
            )
        return {"slots": slots, "files": inputs.get("files") or [],
                "application_summary": "; ".join(f"{k}: {v}" for k, v in slots.items() if v),
                "assumptions": ["Context is derived from user-provided and resolved slot values; verify before engineering decisions."]}

    def op_formulate_ashby_problem(self, inputs: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        slots = inputs.get("slots") or {}
        missing = [slot for slot in SLOT_NAMES if not _text(slots.get(slot))]
        if missing:
            raise ValueError(
                "Ashby formulation is blocked until all six contract slots are populated and confirmed. "
                f"Missing slots: {', '.join(missing)}"
            )
        function = slots["functional_requirement"]
        objective = "Preserve required performance while reducing the stated substitution disadvantage"
        constraints = ["Meet the confirmed functional requirement", "Remain compatible with the application and process conditions"]
        if slots.get("reason_for_substitution"):
            constraints.append(f"Address substitution reason: {slots['reason_for_substitution']}")
        free_variables = ["material family", "composition", "processing route", "cost"]
        return {"function": function, "objective": objective, "constraints": constraints,
                "free_variables": free_variables, "assumptions": ["Draft Ashby formulation; user confirmation is required."]}

    def op_classify_ashby_confirmation(self, inputs: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        return self.op_classify_user_confirmation(inputs, context)

    def op_generate_material_equation(self, inputs: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        ashby = inputs.get("ashby") or {}
        return {"material_index": "M = performance_metric / material_cost (illustrative only)",
                "objective": ashby.get("objective"), "function": ashby.get("function"),
                "variables": ashby.get("free_variables") or [],
                "warning": "Illustrative equation placeholder. A domain expert must derive and validate the actual material index for the selected function and constraints."}

    def op_classify_failure(self, inputs: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        error = inputs.get("error") or {}
        return {"category": error.get("type", "WORKFLOW_ERROR") if isinstance(error, dict) else "WORKFLOW_ERROR",
                "details": error.get("message", str(error)) if isinstance(error, dict) else str(error),
                "recoverable": False}

    # Property-resolution source capabilities. Each returns a normalized attempt.
    def op_resolve_from_knowledge_graph(self, inputs: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        kind = inputs.get("resolution_kind")
        target = inputs.get("target")
        if kind == "baseline_material_properties":
            material = _text(target)
            return {"source": "knowledge_graph", "found": True, "values": {
                "material": material, "density": "unknown - requires verified source", "thermal_limit": "unknown - requires verified source",
                "mechanical_properties": "not available in mock knowledge graph"},
                "evidence": [{"source": "mock_knowledge_graph", "note": "Illustrative placeholder; not a real material property record."}]}
        if kind == "candidate_material_properties":
            candidates = target if isinstance(target, list) else []
            values = {item.get("id", item.get("name", f"candidate_{i}")): {
                "name": item.get("name"), "properties": {"density": None, "thermal_limit": None},
                "property_status": "unverified_mock_data"} for i, item in enumerate(candidates) if isinstance(item, dict)}
            return {"source": "knowledge_graph", "found": True, "values": {"candidates": values},
                    "evidence": [{"source": "mock_knowledge_graph", "note": "Candidate property placeholders; not validated data."}]}
        # Contract slots deliberately proceed through the ordered fallback chain in the demo.
        return {"source": "knowledge_graph", "found": False, "values": {}, "evidence": []}

    def op_resolve_from_web(self, inputs: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        return {"source": "web_search", "found": False, "values": {},
                "evidence": [{"source": "mock_web_search", "note": "No live web connector configured; falling back."}]}

    def op_resolve_with_llm(self, inputs: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        kind = inputs.get("resolution_kind")
        target = inputs.get("target")
        if kind == "contract_slots":
            # Do not fabricate placeholder values for missing contract slots.
            # In this mock implementation the LLM has no evidence from which to
            # infer the user's intended part/product/component/reason. Force the
            # reusable fallback workflow to ask the user instead.
            return {"source": "llm_inference_mock", "found": False, "values": {},
                    "evidence": [{"source": "mock_llm", "note": "No sufficiently grounded value found; asking the user."}]}
        return {"source": "llm_inference_mock", "found": False, "values": {}, "evidence": []}

    def op_merge_resolution_result(self, inputs: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        result = dict(inputs.get("current_result") or {"values": {}, "evidence": [], "unresolved": []})
        result.setdefault("values", {})
        result.setdefault("evidence", [])
        result.setdefault("unresolved", [])
        source = inputs.get("source_result")
        if isinstance(source, dict):
            values = source.get("values") or {}
            if isinstance(values, dict): result["values"].update(values)
            result["evidence"].extend(source.get("evidence") or [])
            result["source"] = source.get("source")
        response = inputs.get("user_response")
        if response:
            parsed = {}
            for slot, aliases in SLOT_ALIASES.items():
                found = _find_slot(_text(response), aliases)
                if found: parsed[slot] = found
            if not parsed and _text(response).lower() not in {"unknown", "i don't know", "not known"}:
                parsed["user_supplied_value"] = _text(response)
            result["values"].update(parsed)
            result["evidence"].append({"source": "user_input", "note": "Value supplied directly by user."})
        return result

    def op_validate_resolution_result(self, inputs: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        result = dict(inputs.get("result") or {})
        result.setdefault("values", {})
        result.setdefault("evidence", [])
        result.setdefault("unresolved", [])
        kind = inputs.get("resolution_kind")
        target = inputs.get("target")
        if kind == "contract_slots" and isinstance(target, list):
            values = result.get("values") if isinstance(result.get("values"), dict) else {}
            # Only non-empty actual values count as resolved. Text such as
            # "not provided" or "unknown" must never satisfy the slot gate.
            unresolved = []
            for slot in target:
                value = values.get(slot)
                normalized = _text(value).lower()
                if not _has_concrete_value(value):
                    unresolved.append(slot)
            result["unresolved"] = unresolved
        result["validated_shape"] = True
        result["warning"] = "Source results in this demo are mocked; verify values against authoritative sources."
        return result

    def op_search_candidate_materials(self, inputs: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        # The demo agent uses the shared ToolCallingAgentRuntime and registered tools.
        runtime = context.services.get("agent_runtime")
        manager = context.services.get("tool_manager")
        if runtime is None or manager is None:
            raise RuntimeError("search_candidate_materials requires agent_runtime and tool_manager services")
        return runtime.run(
            instructions=("Find illustrative candidate materials for the substitution request. "
                          "Call chemical_database_search and compare_chemical_candidates. "
                          "Return candidates with caveats; never claim verified equivalence."),
            inputs={"slots": inputs.get("slots"), "application_context": inputs.get("application_context"),
                    "ashby": inputs.get("ashby"), "equation": inputs.get("equation"),
                    "baseline_properties": inputs.get("baseline_properties")},
            tool_manager=manager,
            tool_ids=["chemical_database_search", "compare_chemical_candidates"],
            context=context,
            max_iterations=6,
        )

    def op_derive_baseline_property_request(self, inputs: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        return {"material": inputs.get("material"), "requested_properties": ["density", "thermal_limit", "mechanical_properties"]}

    def op_derive_candidate_property_request(self, inputs: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        return {"candidates": inputs.get("candidates") or [], "requested_properties": ["density", "thermal_limit", "mechanical_properties"]}

    def op_construct_alternatives(self, inputs: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        candidates = inputs.get("candidates") or []
        candidate_output = inputs.get("candidate_properties") or {}
        values = candidate_output.get("values", {}) if isinstance(candidate_output, dict) else {}
        candidate_values = values.get("candidates", values) if isinstance(values, dict) else {}
        result = []
        for item in candidates:
            if not isinstance(item, dict): continue
            result.append({**item, "properties": candidate_values.get(item.get("id", item.get("name")), {}),
                           "equation": (inputs.get("equation") or {}).get("material_index"),
                           "evidence_status": "mock_unverified"})
        return {"candidates": result, "baseline": inputs.get("baseline_material"),
                "warning": "Candidates and properties are illustrative, not validated substitution recommendations."}

    def op_screen_alternatives(self, inputs: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        passed, rejected = [], []
        for candidate in inputs.get("alternatives") or []:
            if candidate.get("screening_fail"):
                rejected.append({**candidate, "screening_reason": "Failed a configured hard constraint"})
            else:
                passed.append({**candidate, "screening_status": "PROVISIONAL_PASS", "screening_note": "No mock hard-constraint failure; engineering verification required."})
        return {"passed": passed, "rejected": rejected, "constraints_checked": inputs.get("constraints") or [],
                "warning": "Provisional screening only; no safety/compliance decision is implied."}

    def op_rank_alternatives(self, inputs: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        candidates = list(inputs.get("screened_candidates") or [])
        for idx, candidate in enumerate(candidates):
            candidate.setdefault("illustrative_score", round(max(0.5, 0.9 - idx * 0.1), 2))
        candidates.sort(key=lambda x: x.get("illustrative_score", 0), reverse=True)
        for rank, candidate in enumerate(candidates, 1):
            candidate["rank"] = rank
        return {"ranked_candidates": candidates,
                "ranking_method": "mock deterministic ordering; replace with validated Ashby index and evidence-based scoring",
                "warning": "Scores are not real engineering evaluations."}
