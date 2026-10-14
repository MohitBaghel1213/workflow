from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol


class ModelClient(Protocol):
    """Minimal provider-neutral interface for text generation."""

    def complete(self, prompt: str) -> str:
        ...


class RuntimeAdapter(ABC):
    """Framework adapter supplies model access and human-input transport.

    Business capabilities are deliberately not implemented here. They live in
    the shared capability layer and use this adapter's model_client when needed.
    """

    runtime_name = "base"

    @property
    @abstractmethod
    def model_client(self) -> ModelClient:
        raise NotImplementedError

    @abstractmethod
    def request_human_input(self, prompt: str, context: dict[str, Any]) -> str:
        raise NotImplementedError


# Backwards-compatible public name. Runtime now means a runtime adapter, not a
# collection of capability-specific if/else branches.
Runtime = RuntimeAdapter
