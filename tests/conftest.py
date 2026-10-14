from pathlib import Path

import pytest

from main import build_engine
from runtimes.mock_runtime import MockRuntime

ROOT = Path(__file__).parents[1]


class NonInteractiveRuntime(MockRuntime):
    def __init__(self, responses):
        super().__init__(human_input_handler=self._human_input)
        self.responses = iter(responses)
        self.prompts = []

    def _human_input(self, prompt, context):
        self.prompts.append(prompt)
        return next(self.responses)


@pytest.fixture
def non_interactive_runtime_factory():
    return NonInteractiveRuntime


@pytest.fixture
def build_engine_for_test():
    return build_engine
