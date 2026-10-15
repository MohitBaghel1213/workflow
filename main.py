"""Run the framework-independent chemical alternative workflow."""
from __future__ import annotations

import argparse
from pathlib import Path

from runtimes.mock_runtime import MockRuntime
from workflow_engine import WorkflowEngine, WorkflowRegistry, build_capability_executor

ROOT = Path(__file__).resolve().parent
WORKFLOW_DIR = ROOT / "workflows"


def build_engine(workflow_name=None, runtime=None) -> WorkflowEngine:
    """Build the chemical workflow engine; first arg retained for older callers."""
    if runtime is None and workflow_name is not None and not isinstance(workflow_name, str):
        runtime, workflow_name = workflow_name, None
    runtime = runtime or MockRuntime()
    registry = WorkflowRegistry()
    registry.load_directory(WORKFLOW_DIR)
    root_definition = registry.get("chemical-alternative")
    executor = build_capability_executor(runtime)
    return WorkflowEngine(
        root_definition,
        runtime,
        capability_executor=executor,
        workflow_registry=registry,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Chemical alternative workflow demo")
    parser.add_argument("--demo", action="store_true", help="Run the complete workflow with deterministic mock responses")
    parser.add_argument("--prompt", help="User prompt. Use --prompt or interactive input.")
    args = parser.parse_args()

    if args.demo:
        def demo_human_input(prompt, context):
            if "could not reliably resolve" in prompt.lower():
                return "part=handle, product=toothbrush, component=grip"
            return "ACCEPT"
        runtime = MockRuntime(human_input_handler=demo_human_input)
        prompt = args.prompt or (
            "Find an alternative for material=ExamplePolymer, part=handle, product=toothbrush, "
            "component=grip, functional_requirement=durable and water resistant, "
            "reason_for_substitution=reduce cost"
        )
        files = []
    else:
        runtime = MockRuntime()
        prompt = args.prompt or input("Describe the material substitution request: ").strip()
        files = []

    engine = build_engine(runtime)
    print(f"Running {engine.workflow['name']} using runtime={runtime.runtime_name}")
    result = engine.run({"user_prompt": prompt, "files": files, "request_id": "demo-request"})
    print("\nRESULT")
    print(f"status: {result.status}")
    print(f"current_step: {result.current_step}")
    print("output:")
    import json
    print(json.dumps(result.output, indent=2, ensure_ascii=False, default=str))
    if result.status != "COMPLETED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
