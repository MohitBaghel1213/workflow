from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable


class Runtime(ABC):
    """
    Framework-neutral runtime contract.

    A framework adapter implements this interface. The workflow engine never
    imports LangChain, Claude Agent SDK, Microsoft Agent Framework, or any
    model provider.
    """

    @abstractmethod
    def invoke_capability(
        self,
        capability: str,
        inputs: dict[str, Any],
        context: dict[str, Any],
    ) -> Any:
        raise NotImplementedError

    @abstractmethod
    def request_human_input(
        self,
        prompt: str,
        context: dict[str, Any],
    ) -> str:
        raise NotImplementedError
