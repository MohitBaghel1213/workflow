from __future__ import annotations

from typing import Any

from .contracts import CapabilityResult, ExecutionContext
from .registry import CapabilityRegistry


class CapabilityExecutor:
    """Generic capability dispatcher; it contains no capability-specific branches."""

    def __init__(
        self,
        registry: CapabilityRegistry,
        services: dict[str, Any] | None = None,
        *,
        validate_inputs: bool = True,
    ):
        self.registry = registry
        self.services = services or {}
        self.validate_inputs = validate_inputs

    def execute(
        self,
        capability_id: str,
        inputs: dict[str, Any],
        context: ExecutionContext,
    ) -> CapabilityResult:
        handler = self.registry.get(capability_id)
        metadata = self.registry.metadata(capability_id)
        self._validate_inputs(capability_id, inputs, metadata)
        context.services = {**self.services, **context.services}
        result = handler.execute(inputs, context)
        if isinstance(result, CapabilityResult):
            return result
        return CapabilityResult(success=True, output=result)

    def _validate_inputs(
        self,
        capability_id: str,
        inputs: dict[str, Any],
        metadata: dict[str, Any],
    ) -> None:
        if not self.validate_inputs:
            return
        required = metadata.get("required_inputs", [])
        missing = [key for key in required if key not in inputs]
        if missing:
            raise ValueError(
                f"Capability '{capability_id}' is missing required inputs: {missing}"
            )
