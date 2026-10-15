from main import build_engine
from runtimes.mock_runtime import MockRuntime


def test_candidate_research_invokes_registered_tools_through_shared_agent_loop():
    runtime = MockRuntime(human_input_handler=lambda prompt, context: "ACCEPT")
    result = build_engine(runtime=runtime).run({
        "user_prompt": (
            "material=ExamplePolymer, part=handle, product=toothbrush, component=grip, "
            "functional_requirement=durable and water resistant, reason_for_substitution=reduce cost"
        ),
        "files": [],
    })
    assert result.status == "COMPLETED"
    candidates = result.output["candidates"]
    assert [candidate["id"] for candidate in candidates] == ["MAT-101", "MAT-202"]
    assert result.output["ranking"]["ranked_candidates"][0]["rank"] == 1


def test_agent_capability_gets_services_from_executor_not_manual_context():
    from workflow_engine.bootstrap import build_capability_executor
    from workflow_engine.capabilities.contracts import ExecutionContext

    runtime = MockRuntime()
    executor = build_capability_executor(runtime)
    context = ExecutionContext(
        workflow_id="test", workflow_version="1", execution_id="e1",
        step_id="agent_step", runtime_name=runtime.runtime_name, state={},
    )
    result = executor.execute(
        "agent",
        {"properties": {"material": "ExamplePolymer"}},
        context,
        config={
            "instructions": "Find alternatives using available mock tools.",
            "tools": ["chemical_database_search", "compare_chemical_candidates"],
            "max_iterations": 5,
        },
    )
    assert result.success
    assert [item["tool"] for item in result.output["tool_trace"]] == [
        "chemical_database_search", "compare_chemical_candidates"
    ]
