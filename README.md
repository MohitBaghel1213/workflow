# Composable Framework-Independent Declarative Workflow Engine

A runnable reference implementation for composing workflows, sub-workflows, reusable property profiles, shared capabilities, and interchangeable runtime adapters.

The key architectural change is that **capabilities are no longer implemented inside each runtime**. The workflow engine invokes a generic `CapabilityExecutor`; the executor resolves a capability in a registry and invokes its handler. Runtime adapters supply model access and human-input transport, while the same capability handlers are reused across Mock, LangChain, and Claude implementations.

## Architecture

```text
Workflow YAML / Sub-workflows / Property Profiles
                     |
                     v
              WorkflowEngine
   state, routing, retries, nested workflows
                     |
                     v
            CapabilityExecutor
       input checks + registry dispatch
                     |
                     v
            CapabilityRegistry
      capability ID -> handler instance
          /          |           \
         v           v            v
  Python handler  LLM handler  Tool-backed handler
                      |               |
                      v               v
              Runtime.model_client  ToolManager
                      |
          +-----------+------------+
          |           |            |
          v           v            v
        Mock      LangChain      Claude SDK
```

Responsibilities:

- `WorkflowEngine`: state, transitions, conditions, human input, state updates, nested workflows, terminal results.
- `CapabilityRegistry`: registers capability IDs and their handlers/metadata.
- `CapabilityExecutor`: validates required inputs, dispatches handlers, normalizes results. It has no capability-specific `if/else` chain.
- `CapabilityHandler`: reusable implementation of a capability such as property extraction, validation, or confirmation classification.
- `AgentCapability`: generic wrapper that reads agent instructions/tool allowlists from YAML and delegates to the shared agent runtime.
- `ToolCallingAgentRuntime`: owns the reusable model → tool → result → model loop. New agentic capabilities do not implement their own loop.
- `ToolManager` (`ToolRegistry` alias): registry/dispatcher for concrete tools used by capabilities (MCP, HTTP, databases, etc.).
- `RuntimeAdapter`: supplies a `model_client` and human-input transport. It does not implement business capabilities.
- `WorkflowRegistry`: resolves sub-workflow IDs to YAML definitions.
- Property profile loader: resolves profile composition using `includes` or `extends`.


### Agent tool-calling demo

The advanced workflow maps the business capability `find_chemical_alternatives` to the reusable `agent` implementation in YAML. `AgentCapability` delegates to `ToolCallingAgentRuntime`, which owns the only tool-calling loop. Shared services are injected by `CapabilityExecutor`, so callers do not need to manually provide `tool_manager` or a tool-calling model in each execution context.

```bash
python main.py --workflow advanced --demo
python -m pytest -q
```

The mock demo runs without credentials. `MockToolCallingModel` deterministically calls the configured tools in order; it is for architecture demonstrations, not a real LLM planner. The LangChain and Claude adapters currently provide text-completion interfaces; to use real provider-driven tool selection, implement the `ToolCallingModel.next_action(messages, tools)` contract and inject it into `ToolCallingAgentRuntime`.

## Project structure

```text
framework_independent_declarative_workflow/
├── workflow.yaml                         # Basic top-level workflow
├── workflows/
│   ├── property_collection.yaml          # Reusable sub-workflow
│   └── chemical_alternative_advanced.yaml # Seven-property composition
├── profiles/property_profiles.yaml       # Reusable property groups/profiles
├── workflow_engine/
│   ├── engine.py
│   ├── bootstrap.py
│   ├── registry.py
│   ├── loader.py
│   ├── expression.py
│   ├── runtime.py
│   └── capabilities/
│       ├── contracts.py
│       ├── registry.py
│       ├── executor.py
│       └── handlers.py
├── tools/manager.py
├── TOOL_CALLING_WALKTHROUGH.md               # End-to-end agent/tool call path
├── runtimes/
│   ├── mock_runtime.py
│   ├── langchain_runtime.py
│   ├── claude_runtime.py
│   └── llm_utils.py
├── examples/
├── tests/
└── main.py
```

## Install and run

Python 3.11 or newer is recommended.

### Local mock runtime (no API key)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Enter values using `property_id=value` syntax. The basic workflow requires five fields:

```text
product_type=paint chemical_name=chemX concentration=10% application=coating temperature=80C
```

If a field is missing, the workflow asks for it. Confirm with `yes`, or correct a field with `temperature=120C`.

Run the advanced profile (seven fields):

```powershell
python main.py --workflow advanced
```

The advanced profile also requires `pressure` and `viscosity`.

### Complete tool-calling demonstration (no API key)

```powershell
python main.py --workflow advanced --demo
```

This executes property extraction and confirmation, then invokes the `find_chemical_alternatives` capability. That capability obtains tool schemas from `ToolManager`, passes them to a deterministic mock tool-calling model, executes requested tools through the registry, feeds tool results back into the model loop, and returns ranked mock candidates plus a tool trace. See `TOOL_CALLING_WALKTHROUGH.md`. The mock model decisions, candidate data, and scores are illustrative only.

### LangChain runtime

```powershell
pip install -r requirements-langchain.txt
$env:OPENAI_API_KEY="your-key"
$env:LANGCHAIN_MODEL="gpt-4o-mini"
python examples/langchain_usage.py
```

For an OpenAI-compatible endpoint, set `LANGCHAIN_BASE_URL` and the relevant API key/model environment variables.

### Claude Agent SDK runtime

```powershell
pip install -r requirements-claude.txt
$env:ANTHROPIC_API_KEY="your-key"
$env:ANTHROPIC_MODEL="claude-sonnet-4-5"
python examples/claude_usage.py
```

The Claude adapter uses the SDK `query()` API to provide the same simple text-completion contract used by shared LLM capabilities. It does not execute workflow steps or own capability dispatch.

### Tests

```powershell
pip install -r requirements-dev.txt
pytest -q
```

The tests run without network access or provider API keys.

## How composition works

### 1. Top-level workflow calls a reusable sub-workflow

The root `workflow.yaml` invokes `property-collection` and passes a profile:

```yaml
- id: collect_properties
  type: workflow
  workflow: property-collection
  input:
    user_prompt: "${input.user_prompt}"
    property_profile: "${profiles.chemical_basic}"
```

The advanced workflow passes `${profiles.chemical_advanced}` to the exact same sub-workflow. No extraction/validation logic is duplicated.

### 2. Property profiles compose smaller groups

In `profiles/property_profiles.yaml`:

- `chemical_basic` includes `common_product` + `chemical_core` = five properties.
- `chemical_advanced` includes `chemical_basic` + `chemical_operating_conditions` = seven properties.

`load_profiles()` resolves `includes` and `extends`, preserves declaration order, permits later definitions to override earlier property definitions by ID, and detects unknown/circular references.

### 3. Add a capability without changing the executor

Implement a handler with this contract:

```python
class MyCapability:
    def execute(self, inputs, context):
        return {"result": "..."}
```

Register it once during application setup:

```python
registry.register(
    "my_capability",
    MyCapability(),
    metadata={"required_inputs": ["value"]},
)
```

Then reference it in YAML:

```yaml
- id: do_something
  type: capability
  capability: my_capability
  input:
    value: "${input.some_value}"
  output:
    target: state.my_result
  on_success:
    next: next_step
```

The generic executor does not need to change.

### 4. Use a registered tool from a capability

`ToolManager` registers concrete tool integrations. A tool-backed capability can call `context.services["tool_manager"].execute(tool_id, inputs, context)`. The project includes a mock chemical database search tool to demonstrate this extension point; it deliberately returns no real chemical candidates until connected to an actual data source.

### 5. Add a runtime

Implement `RuntimeAdapter` with:

- `runtime_name`
- a `model_client` whose `complete(prompt)` method returns text
- `request_human_input(prompt, context)`

The shared capability handlers and YAML do not need to change. If a capability genuinely requires runtime-specific agent orchestration, implement that capability as a small adapter/handler that uses the runtime service, rather than adding branches to `CapabilityExecutor`.

## Expression roots

Workflow expressions support:

- `${input.some_field}` — workflow input
- `${state.some_field}` — mutable workflow state
- `${schemas.some_schema}` — local schemas
- `${profiles.profile_id}` — resolved profile configuration
- `${error}` — current execution error

An expression that is the entire value preserves its type (dict/list/etc.). Embedded expressions are interpolated as strings.

## Important implementation notes

- The included `MockRuntime` is deterministic and fully local; it understands `property_id=value` demo syntax.
- `LangChainRuntime` and `ClaudeRuntime` require their respective optional dependencies and provider credentials.
- The sample `chemical_search` tool is a stub, not a chemical recommendation engine.
- The engine is synchronous for this reference implementation. The Claude adapter bridges the SDK's async query API when no event loop is already running; an application hosted inside an async event loop should introduce an async engine/adapter rather than nesting `asyncio.run()`.
- Durable checkpoints, resumable human-in-the-loop sessions, authentication/authorization, audit logs, and production-grade retry/backoff are follow-on production concerns.

## Extending the engine with new step types

The core `WorkflowEngine` does not dispatch with a step-type `if/else` chain. It
resolves each step's `type` through `StepHandlerRegistry`. Type-specific
validation and execution live in registered handlers; workflow-wide invariants
such as duplicate IDs and valid graph edges are checked by `WorkflowValidator`.

To add a step type:

1. Implement `validate(step)` and `execute(step, context)` on a handler.
2. Return a `StepOutcome` from `execute`.
3. Register it in `build_step_handler_registry()` (or register it in a custom
   registry passed to `WorkflowEngine`).

Example:

```python
from workflow_engine import (
    StepOutcome, WorkflowEngine, WorkflowDefinitionError, build_step_handler_registry
)

class AuditStepHandler:
    def validate(self, step):
        if not step.get("next"):
            raise WorkflowDefinitionError("audit step requires next")

    def execute(self, step, context):
        context.workflow_context.state["audit_marker"] = step.get("message", "audited")
        return StepOutcome(next_step=step["next"])

registry = build_step_handler_registry()
registry.register("audit", AuditStepHandler())
engine = WorkflowEngine(definition, runtime, step_handler_registry=registry)
```

Do not create a new step type for each business capability. Prefer the existing
`type: capability` primitive with a new registered capability handler. Add a
new step type only when it introduces a genuinely different orchestration
primitive (for example `parallel`, `foreach`, or an explicit approval gate).
