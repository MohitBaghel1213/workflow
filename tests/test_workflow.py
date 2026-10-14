from conftest import NonInteractiveRuntime
from main import build_engine


def test_basic_workflow_completes_without_missing_information():
    runtime = NonInteractiveRuntime(["yes"])
    engine = build_engine("basic", runtime)
    result = engine.run({
        "user_prompt": (
            "product_type=paint chemical_name=chemX concentration=10% "
            "application=coating temperature=80C"
        )
    })
    assert result.status == "COMPLETED"
    properties = result.output["result"]["properties"]
    assert properties["product_type"] == "paint"
    assert result.output["result"]["confirmation_status"] == "CONFIRMED"


def test_missing_property_uses_human_input_and_reextracts():
    runtime = NonInteractiveRuntime(["pressure=5bar viscosity=low", "yes"])
    engine = build_engine("advanced", runtime)
    result = engine.run({
        "user_prompt": (
            "product_type=paint chemical_name=chemX concentration=10% "
            "application=coating temperature=80C"
        )
    })
    assert result.status == "COMPLETED"
    properties = result.output["result"]["properties"]
    assert properties["pressure"] == "5bar"
    assert properties["viscosity"] == "low"
    assert len(runtime.prompts) == 2


def test_confirmation_correction_is_revalidated():
    runtime = NonInteractiveRuntime(["temperature=120C", "yes"])
    engine = build_engine("basic", runtime)
    result = engine.run({
        "user_prompt": (
            "product_type=paint chemical_name=chemX concentration=10% "
            "application=coating temperature=80C"
        )
    })
    assert result.status == "COMPLETED"
    assert result.output["result"]["properties"]["temperature"] == "120C"


def test_basic_and_advanced_use_different_profiles():
    basic_runtime = NonInteractiveRuntime(["yes"])
    basic = build_engine("basic", basic_runtime).run({
        "user_prompt": "product_type=p chemical_name=c concentration=1 application=a temperature=t"
    })
    assert basic.status == "COMPLETED"
    assert "pressure" not in basic.output["result"]["properties"]

    advanced_runtime = NonInteractiveRuntime(["pressure=p viscosity=v", "yes"])
    advanced = build_engine("advanced", advanced_runtime).run({
        "user_prompt": "product_type=p chemical_name=c concentration=1 application=a temperature=t"
    })
    assert advanced.status == "COMPLETED"
    assert advanced.output["result"]["properties"]["pressure"] == "p"
