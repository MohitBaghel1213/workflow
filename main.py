"""Run the composable workflow using the local mock runtime."""
from __future__ import annotations

import argparse
from pathlib import Path

from runtimes.mock_runtime import MockRuntime
from workflow_engine import (
    WorkflowEngine,
    WorkflowRegistry,
    build_capability_executor,
    load_profiles,
    load_workflow,
)

ROOT = Path(__file__).resolve().parent


def build_engine(workflow_name: str = "basic", runtime=None) -> WorkflowEngine:
    runtime = runtime or MockRuntime()
    profiles = load_profiles(ROOT / "profiles" / "property_profiles.yaml")
    registry = WorkflowRegistry()
    registry.load_directory(ROOT / "workflows")
    root_definition = (
        load_workflow(ROOT / "workflow.yaml")
        if workflow_name == "basic"
        else registry.get("chemical-alternative-advanced")
    )
    registry.register(root_definition)
    executor = build_capability_executor(runtime)
    return WorkflowEngine(
        root_definition,
        runtime,
        capability_executor=executor,
        workflow_registry=registry,
        profiles=profiles,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Composable declarative workflow demo")
    parser.add_argument("--workflow", choices=["basic", "advanced"], default="basic")
    parser.add_argument("--demo", action="store_true", help="Run a complete no-API-key tool-calling demonstration")
    args = parser.parse_args()
    if args.demo:
        runtime = MockRuntime(human_input_handler=lambda prompt, context: "yes")
    else:
        runtime = MockRuntime()
    engine = build_engine(args.workflow, runtime=runtime)
    print(f"Running {engine.workflow['name']} with runtime={engine.runtime.runtime_name}")
    if args.demo:
        prompt = (
            "chemical_name=ExampleSolvent concentration=10% temperature=25C "
            "product_type=industrial_cleaner application=surface_cleaning "
            "pressure=1bar viscosity=low"
        )
        print(f"\n[demo] Input: {prompt}")
    else:
        prompt = input("Describe the chemical/product (property_id=value syntax works best): ").strip()
    result = engine.run({"user_prompt": prompt})
    print("\nRESULT")
    print(f"status: {result.status}")
    print(f"output: {result.output}")


if __name__ == "__main__":
    main()
