from conftest import NonInteractiveRuntime
import pytest
from workflow_engine.errors import WorkflowExecutionError
from main import build_engine


def complete_prompt():
    return (
        "material=ExamplePolymer, part=handle, product=toothbrush, component=grip, "
        "functional_requirement=durable and water resistant, reason_for_substitution=reduce cost"
    )


def test_chemical_workflow_completes_end_to_end_with_mock_data():
    runtime = NonInteractiveRuntime(["ACCEPT", "ACCEPT"])
    result = build_engine(runtime=runtime).run({"user_prompt": complete_prompt(), "files": [], "request_id": "test-1"})
    assert result.status == "COMPLETED"
    assert result.output["slots"]["material"] == "ExamplePolymer"
    assert result.output["ashby"]["function"]
    assert result.output["equation"]["material_index"]
    assert len(result.output["candidates"]) == 2
    assert len(result.output["ranking"]["ranked_candidates"]) == 2


def test_missing_optional_slots_use_reusable_resolution_and_user_fallback():
    runtime = NonInteractiveRuntime([
        "ACCEPT",  # initial slot confirmation
        "part=handle, product=toothbrush, component=grip",  # final source fallback
        "ACCEPT",  # confirm resolved slots
        "ACCEPT",  # confirm Ashby formulation
    ])
    result = build_engine(runtime=runtime).run({
        "user_prompt": "material=ExamplePolymer, functional_requirement=durable, reason_for_substitution=cost",
        "files": [],
    })
    assert result.status == "COMPLETED"
    assert result.output["slots"]["part"] == "handle"
    assert result.output["slots"]["product"] == "toothbrush"
    assert any("could not reliably resolve" in prompt.lower() for prompt in runtime.prompts)


def test_material_is_mandatory_and_requested_if_missing():
    runtime = NonInteractiveRuntime([
        "ExamplePolymer",  # mandatory material prompt
        "ACCEPT",          # confirm extracted slots
        "part=handle, product=toothbrush, component=grip, reason_for_substitution=reduce cost",  # fallback for other slots
        "ACCEPT",          # confirm resolved slots
        "ACCEPT",          # Ashby confirmation
    ])
    result = build_engine(runtime=runtime).run({"user_prompt": "product=toothbrush, functional_requirement=durable", "files": []})
    assert result.status == "COMPLETED"
    assert result.output["slots"]["material"] == "ExamplePolymer"


def test_workflow_registry_contains_only_new_workflows():
    engine = build_engine(runtime=NonInteractiveRuntime([]))
    assert engine.workflow["id"] == "chemical-alternative"
    assert sorted(engine.workflow_registry.ids()) == ["chemical-alternative", "property-resolution"]


def test_optional_files_input_defaults_to_empty_array():
    runtime = NonInteractiveRuntime(["ACCEPT", "ACCEPT"])
    # `files` and `request_id` are intentionally omitted. The workflow schema
    # supplies files=[] and the complete workflow should still run.
    result = build_engine(runtime=runtime).run({"user_prompt": complete_prompt()})
    assert result.status == "COMPLETED"
    assert result.state["execution"]["total_steps"] > 0


def test_explicit_null_files_is_rejected_with_clear_type_error():
    runtime = NonInteractiveRuntime(["ACCEPT", "ACCEPT"])
    # Explicit null is different from an omitted optional input; callers that
    # supply files must provide an array.
    with pytest.raises(WorkflowExecutionError, match="Input 'files' must be of type array"):
        build_engine(runtime=runtime).run({"user_prompt": complete_prompt(), "files": None})


def test_missing_slots_are_resolved_in_repeated_fallback_rounds_before_ashby():
    runtime = NonInteractiveRuntime([
        "ACCEPT",  # initial slot confirmation
        "part=handle",  # first fallback round resolves only part
        "component=grip, reason_for_substitution=reduce cost",  # second fallback round
        "ACCEPT",  # confirm all six slots
        "ACCEPT",  # confirm Ashby formulation
    ])
    result = build_engine(runtime=runtime).run({
        "user_prompt": "material=ExamplePolymer, product=toothbrush, functional_requirement=durable",
        "files": [],
    })
    assert result.status == "COMPLETED"
    assert set(result.output["slots"]) >= {
        "material", "part", "product", "component",
        "functional_requirement", "reason_for_substitution",
    }
    assert all(result.output["slots"][key] for key in (
        "material", "part", "product", "component",
        "functional_requirement", "reason_for_substitution",
    ))
    prompts = [prompt.lower() for prompt in runtime.prompts]
    assert sum("could not reliably resolve" in prompt for prompt in prompts) == 2
    # The second fallback round must happen before the Ashby confirmation prompt.
    assert next(i for i, prompt in enumerate(prompts) if "review the proposed ashby formulation" in prompt) > max(
        i for i, prompt in enumerate(prompts) if "could not reliably resolve" in prompt
    )
