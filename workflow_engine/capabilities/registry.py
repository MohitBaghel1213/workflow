from __future__ import annotations

from typing import Any

from workflow_engine.errors import CapabilityNotFoundError


class CapabilityRegistry:
    """Maps stable capability IDs to implementation objects."""

    def __init__(self):
        self._handlers: dict[str, Any] = {}
        self._metadata: dict[str, dict[str, Any]] = {}

    def register(
        self,
        capability_id: str,
        handler: Any,
        *,
        metadata: dict[str, Any] | None = None,
        replace: bool = False,
    ) -> None:
        if capability_id in self._handlers and not replace:
            raise ValueError(f"Capability '{capability_id}' is already registered")
        self._handlers[capability_id] = handler
        self._metadata[capability_id] = dict(metadata or {})

    def get(self, capability_id: str) -> Any:
        try:
            return self._handlers[capability_id]
        except KeyError as exc:
            raise CapabilityNotFoundError(
                f"Capability '{capability_id}' is not registered"
            ) from exc

    def metadata(self, capability_id: str) -> dict[str, Any]:
        self.get(capability_id)
        return dict(self._metadata[capability_id])

    def contains(self, capability_id: str) -> bool:
        return capability_id in self._handlers

    def ids(self) -> list[str]:
        return sorted(self._handlers)
