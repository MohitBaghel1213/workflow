from workflow_engine.bootstrap import build_capability_executor, build_capability_registry, build_tool_manager
from workflow_engine.capabilities.contracts import ExecutionContext
from runtimes.mock_runtime import MockRuntime


def context(runtime):
    return ExecutionContext(
        workflow_id="test", workflow_version="1", execution_id="e1",
        step_id="s1", runtime_name=runtime.runtime_name, state={},
    )


def test_validation_capability_is_runtime_independent():
    runtime = MockRuntime()
    executor = build_capability_executor(runtime)
    result = executor.execute("validation", {
        "properties": {"property_a": "A"},
        "property_profile": {"properties": [
            {"id": "property_a", "type": "string", "required": True},
            {"id": "property_b", "type": "string", "required": True},
        ]},
    }, context(runtime))
    assert result.success
    assert result.output["validation_status"] == "INVALID"
    assert result.output["missing_properties"] == ["property_b"]


def test_capability_registry_lists_shared_capabilities():
    registry = build_capability_registry()
    assert "property_extraction" in registry.ids()
    assert "validation" in registry.ids()
    assert "chemical_search" in registry.ids()


def test_tool_manager_dispatches_registered_tool():
    manager = build_tool_manager()
    result = manager.execute("chemical_database_search", {"query": "chemical X"}, context(MockRuntime()))
    assert result["query"] == "chemical X"
    assert result["candidates"] == []


def test_tool_backed_capability_uses_tool_manager():
    runtime = MockRuntime()
    executor = build_capability_executor(runtime)
    result = executor.execute("chemical_search", {"query": "chemical X"}, context(runtime))
    assert result.success
    assert result.output["query"] == "chemical X"
