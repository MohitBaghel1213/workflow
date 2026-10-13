from pathlib import Path

from workflow_engine import WorkflowEngine, load_workflow
from runtimes.mock_runtime import MockRuntime


ROOT = Path(__file__).parents[1]


def build_engine():
    definition = load_workflow(ROOT / "workflow.yaml")
    return WorkflowEngine(definition, MockRuntime())


class NonInteractiveRuntime(MockRuntime):
    def __init__(self, responses):
        self.responses = iter(responses)

    def request_human_input(self, prompt, context):
        return next(self.responses)


def test_complete_without_hitl():
    definition = load_workflow(ROOT / "workflow.yaml")
    runtime = NonInteractiveRuntime(["yes"])
    engine = WorkflowEngine(definition, runtime)

    result = engine.run({
        "user_prompt": (
            "property_a=A property_b=B property_c=C "
            "property_d=D property_e=E"
        )
    })

    assert result.status == "COMPLETED"
    assert result.output["properties"]["property_a"] == "A"


def test_missing_property_uses_hitl_and_reextracts():
    definition = load_workflow(ROOT / "workflow.yaml")
    runtime = NonInteractiveRuntime([
        "property_e=E",
        "yes",
    ])
    engine = WorkflowEngine(definition, runtime)

    result = engine.run({
        "user_prompt": (
            "property_a=A property_b=B property_c=C property_d=D"
        )
    })

    assert result.status == "COMPLETED"
    assert result.output["properties"]["property_e"] == "E"


def test_confirmation_correction_is_revalidated():
    definition = load_workflow(ROOT / "workflow.yaml")
    runtime = NonInteractiveRuntime([
        "property_c=CORRECTED",
        "yes",
    ])
    engine = WorkflowEngine(definition, runtime)

    result = engine.run({
        "user_prompt": (
            "property_a=A property_b=B property_c=C "
            "property_d=D property_e=E"
        )
    })

    assert result.status == "COMPLETED"
    assert result.output["properties"]["property_c"] == "CORRECTED"
