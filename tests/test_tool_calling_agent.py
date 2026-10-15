from main import build_engine
from runtimes.mock_runtime import MockRuntime


def test_advanced_workflow_invokes_tools_through_agent_loop():
    runtime = MockRuntime(human_input_handler=lambda prompt, context: "yes")
    engine = build_engine("advanced", runtime=runtime)
    result = engine.run({
        "user_prompt": (
            "product_type=industrial_cleaner chemical_name=ExampleSolvent "
            "concentration=10% application=surface_cleaning temperature=25C "
            "pressure=1bar viscosity=low"
        )
    })

    assert result.status == "COMPLETED"
    alternatives = result.output["alternatives"]
    assert [item["tool"] for item in alternatives["tool_trace"]] == [
        "chemical_database_search",
        "compare_chemical_candidates",
    ]
    assert len(alternatives["candidates"]) == 2
    assert alternatives["model_mode"] == "scripted-mock-tool-calling-model"


def test_agent_capability_gets_tool_services_from_executor_not_manual_context():
    """Regression: callers do not have to manually inject tool_manager/model services."""
    from workflow_engine.bootstrap import build_capability_executor
    from workflow_engine.capabilities.contracts import ExecutionContext

    runtime = MockRuntime(human_input_handler=lambda prompt, context: "yes")
    executor = build_capability_executor(runtime)
    context = ExecutionContext(
        workflow_id="test", workflow_version="1", execution_id="e1",
        step_id="agent_step", runtime_name=runtime.runtime_name, state={},
    )
    result = executor.execute(
        "agent",
        {"properties": {"chemical_name": "chemX", "application": "demo"}},
        context,
        config={
            "instructions": "Find alternatives using the available mock tools.",
            "tools": ["chemical_database_search", "compare_chemical_candidates"],
            "max_iterations": 5,
        },
    )

    assert result.success
    assert [item["tool"] for item in result.output["tool_trace"]] == [
        "chemical_database_search", "compare_chemical_candidates"
    ]
