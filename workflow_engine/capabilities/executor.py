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
        *,
        implementation_id: str | None = None,
        config: dict[str, Any] | None = None,
        required_inputs: list[str] | None = None,
    ) -> CapabilityResult:
        # A business capability ID can be mapped declaratively to a reusable
        # implementation (for example, any YAML-defined agent maps to "agent").
        handler_id = implementation_id or capability_id
        handler = self.registry.get(handler_id)
        metadata = self.registry.metadata(handler_id)
        if required_inputs is not None:
            metadata = {**metadata, "required_inputs": required_inputs}
        self._validate_inputs(capability_id, inputs, metadata)
        context.services = {**self.services, **context.services}
        context.config = {**(config or {}), **context.config}
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
