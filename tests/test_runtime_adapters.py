from runtimes.claude_runtime import ClaudeRuntime
from runtimes.langchain_runtime import LangChainRuntime


class FakeLangChainResponse:
    content = '{"property_a":"A","property_b":"B"}'


class FakeLangChainModel:
    def __init__(self):
        self.prompts = []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        return FakeLangChainResponse()


class FakeClaudeRuntime(ClaudeRuntime):
    def __init__(self):
        self.model = "fake"
        self.human_input_handler = lambda p, c: "yes"

    def _invoke_agent(self, prompt):
        return '{"property_a":"A","property_b":"B"}'


def test_langchain_runtime_real_adapter_contract():
    runtime = LangChainRuntime(model=FakeLangChainModel(), human_input_handler=lambda p, c: "yes")
    result = runtime.invoke_capability(
        "property_extraction",
        {"user_prompt": "find values", "existing_properties": {}},
        {},
    )
    assert result == {"property_a": "A", "property_b": "B"}

    validation = runtime.invoke_capability(
        "validation",
        {
            "properties": result,
            "schema": {"required": ["property_a", "property_b"]},
        },
        {},
    )
    assert validation["validation_status"] == "VALID"


def test_claude_runtime_real_adapter_contract():
    runtime = FakeClaudeRuntime()
    result = runtime.invoke_capability(
        "property_extraction",
        {"user_prompt": "find values", "existing_properties": {}},
        {},
    )
    assert result == {"property_a": "A", "property_b": "B"}

    confirmation = runtime.invoke_capability(
        "confirmation_classification",
        {
            "response": "yes",
            "current_properties": {"property_a": "A"},
        },
        {},
    )
    assert confirmation["decision"] in {"CONFIRMED", "CORRECTION_REQUIRED", "UNCLEAR"}
