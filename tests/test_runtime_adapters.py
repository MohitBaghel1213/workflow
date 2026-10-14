from runtimes.claude_runtime import ClaudeRuntime
from runtimes.langchain_runtime import LangChainRuntime
from workflow_engine.bootstrap import build_capability_executor
from workflow_engine.capabilities.contracts import ExecutionContext


class FakeLangChainResponse:
    content = '{"product_type":"paint"}'


class FakeLangChainModel:
    def invoke(self, prompt):
        return FakeLangChainResponse()


class FakeModelClient:
    def complete(self, prompt):
        if "TASK:PROPERTY_EXTRACTION" in prompt:
            return '{"product_type":"paint"}'
        return '{"decision":"CONFIRMED","corrections":{}}'


def _context(runtime):
    return ExecutionContext("test", "1", "e1", "step1", runtime.runtime_name, {})


def test_langchain_adapter_supplies_model_client_to_shared_capability():
    runtime = LangChainRuntime(model=FakeLangChainModel(), human_input_handler=lambda p, c: "yes")
    executor = build_capability_executor(runtime)
    result = executor.execute("property_extraction", {
        "user_prompt": "product_type=paint",
        "existing_properties": {},
        "property_profile": {"properties": [{"id": "product_type", "required": True}]},
    }, _context(runtime))
    assert result.output == {"product_type": "paint"}


def test_claude_adapter_uses_shared_capability_executor_without_sdk_import():
    runtime = ClaudeRuntime(model_client=FakeModelClient(), human_input_handler=lambda p, c: "yes")
    executor = build_capability_executor(runtime)
    result = executor.execute("confirmation_classification", {
        "response": "yes", "current_properties": {"product_type": "paint"},
    }, _context(runtime))
    assert result.output["decision"] == "CONFIRMED"
