"""Run the fully local mock runtime."""

from pathlib import Path

from workflow_engine.engine import WorkflowEngine
from workflow_engine.loader import load_workflow
from runtimes.mock_runtime import MockRuntime


ROOT = Path(__file__).resolve().parent


def main() -> None:
    definition = load_workflow(ROOT / "workflow.yaml")
    engine = WorkflowEngine(definition, MockRuntime())
    result = engine.run({
        "user_prompt": input(
            "Initial prompt (e.g. property_a=A property_b=B ...): "
        ).strip()
    })
    print("\nRESULT")
    print(result)


if __name__ == "__main__":
    main()
