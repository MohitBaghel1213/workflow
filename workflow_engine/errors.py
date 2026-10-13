class WorkflowError(Exception):
    """Base workflow engine exception."""


class WorkflowDefinitionError(WorkflowError):
    """Raised when a workflow definition is invalid."""


class CapabilityNotFoundError(WorkflowError):
    """Raised when a runtime does not provide a required capability."""


class WorkflowExecutionError(WorkflowError):
    """Raised for execution failures."""


class HumanInputRequired(WorkflowError):
    """Signals that execution must suspend for human input."""
    def __init__(self, step_id: str, prompt: str, target: str):
        super().__init__(prompt)
        self.step_id = step_id
        self.prompt = prompt
        self.target = target
