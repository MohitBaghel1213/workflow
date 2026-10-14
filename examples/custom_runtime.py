"""Example of plugging in a custom model/runtime without implementing capabilities."""
from typing import Any
from main import build_engine
from workflow_engine.runtime import RuntimeAdapter


class MyModelClient:
    def complete(self, prompt: str) -> str:
        # Replace with your model/framework call. Must return text.
        raise NotImplementedError


class MyRuntime(RuntimeAdapter):
    runtime_name = "my-runtime"

    def __init__(self):
        self._model_client = MyModelClient()

    @property
    def model_client(self):
        return self._model_client

    def request_human_input(self, prompt: str, context: dict[str, Any]) -> str:
        return input(f"\n{prompt}\n> ")


if __name__ == "__main__":
    # The workflow and capability handlers are reused; only the runtime adapter changes.
    engine = build_engine("basic", MyRuntime())
    print(engine.run({"user_prompt": input("Initial prompt: ").strip()}))
