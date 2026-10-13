"""Run the unchanged workflow.yaml using the Claude runtime."""

from pathlib import Path

from workflow_engine.engine import WorkflowEngine
from workflow_engine.loader import load_workflow
from runtimes.claude_runtime import ClaudeRuntime


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    definition = load_workflow(ROOT / "workflow.yaml")
    runtime = ClaudeRuntime()
    engine = WorkflowEngine(definition, runtime)

    result = engine.run({
        "user_prompt": input(
            "Initial prompt: "
        ).strip()
    })

    print("\nRESULT")
    print(result)


if __name__ == "__main__":
    main()
