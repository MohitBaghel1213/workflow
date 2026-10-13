"""Run the unchanged workflow.yaml using the LangChain runtime."""

from pathlib import Path

from workflow_engine.engine import WorkflowEngine
from workflow_engine.loader import load_workflow
from runtimes.langchain_runtime import LangChainRuntime
from runtimes.llm_utils import model


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    definition = load_workflow(ROOT / "workflow.yaml")
    runtime = LangChainRuntime(model=model)
    engine = WorkflowEngine(definition, runtime)

    result = engine.run({
        "user_prompt": input(
            "Ask me anything:"
        ).strip()
    })

    print("\nRESULT")
    print(result)


if __name__ == "__main__":
    main()
