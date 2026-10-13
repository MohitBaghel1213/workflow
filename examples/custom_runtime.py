"""
Minimal custom runtime example.

This is the key extensibility point: a completely different framework can
consume the same workflow YAML by implementing Runtime.
"""

from pathlib import Path

from workflow_engine import WorkflowEngine, Runtime, load_workflow


class MyFrameworkRuntime(Runtime):

    def invoke_capability(self, capability, inputs, context):
        handlers = {
            "property_extraction": self.extract,
            "validation": self.validate,
            "failure_classification": self.classify_failure,
            "confirmation_classification": self.classify_confirmation,
        }

        if capability not in handlers:
            raise ValueError(f"Unsupported capability: {capability}")

        return handlers[capability](inputs, context)

    def request_human_input(self, prompt, context):
        return input(f"\n{prompt}\n> ")

    def extract(self, inputs, context):
        # Replace with any framework/agent implementation.
        raise NotImplementedError

    def validate(self, inputs, context):
        properties = inputs["properties"]
        required = inputs["schema"]["required"]
        missing = [p for p in required if not properties.get(p)]
        return {
            "validation_status": "VALID" if not missing else "INVALID",
            "missing_properties": missing,
            "validation_errors": [
                {
                    "property": name,
                    "code": "REQUIRED_PROPERTY_MISSING",
                    "message": f"{name} is required",
                }
                for name in missing
            ],
        }

    def classify_failure(self, inputs, context):
        return "SYSTEM_ERROR"

    def classify_confirmation(self, inputs, context):
        raise NotImplementedError


definition = load_workflow(Path(__file__).parents[1] / "workflow.yaml")
engine = WorkflowEngine(definition, MyFrameworkRuntime())

# Same YAML. Different runtime.
result = engine.run({
    "user_prompt": "application input"
})
print(result)
