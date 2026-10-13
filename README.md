# Framework-Independent Declarative Workflow — Three Runnable Runtimes

This project demonstrates one **framework-neutral `workflow.yaml`** executed by the same generic `WorkflowEngine` with three interchangeable runtimes:

1. **MockRuntime** — fully local; no API key.
2. **LangChainRuntime** — real LangChain model execution through `langchain-openai` and an OpenAI-compatible chat endpoint.
3. **ClaudeRuntime** — real Claude Agent SDK execution using the Claude agent harness.

The key architectural rule is:

```text
workflow.yaml
     |
     v
WorkflowEngine          <- framework-independent
     |
     +------------------+------------------+
     |                  |                  |
     v                  v                  v
MockRuntime       LangChainRuntime   ClaudeRuntime
     |                  |                  |
  local logic      LangChain model      Claude API
```

Changing from LangChain to Claude does **not** require changing `workflow.yaml` or `WorkflowEngine`.

## 1. Project structure

```text
framework_independent_declarative_workflow/
├── workflow.yaml
├── workflow_engine/
│   ├── engine.py
│   ├── runtime.py
│   ├── loader.py
│   ├── expression.py
│   ├── models.py
│   └── errors.py
├── runtimes/
│   ├── mock_runtime.py
│   ├── langchain_runtime.py
│   ├── claude_runtime.py
│   └── llm_utils.py
├── examples/
│   ├── langchain_usage.py
│   ├── claude_usage.py
│   └── custom_runtime.py
├── tests/
├── main.py
├── requirements.txt
├── requirements-langchain.txt
├── requirements-claude.txt
├── requirements-all.txt
└── .env.example
```

## 2. Install

Create a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

For only the local runtime:

```powershell
pip install -r requirements.txt
```

For LangChain:

```powershell
pip install -r requirements-langchain.txt
```

For Claude:

```powershell
pip install -r requirements-claude.txt
```

For everything + tests:

```powershell
pip install -r requirements-all.txt
```

## 3. Run MockRuntime — no API key

```powershell
python main.py
```

Example initial input:

```text
property_a=A property_b=B property_c=C
```

The workflow will ask for missing properties. You can respond with:

```text
property_d=D property_e=E
```

It will then show the extracted values and ask for confirmation.

Confirm with:

```text
yes
```

Or test corrections:

```text
property_c=CORRECTED_VALUE
```

## 4. Run LangChainRuntime

Set the API key in PowerShell:

```powershell
$env:OPENAI_API_KEY="your-key"
```

Optional model:

```powershell
$env:LANGCHAIN_MODEL="gpt-4o-mini"
```

Then:

```powershell
python examples/langchain_usage.py
```

### OpenAI-compatible providers

`LangChainRuntime` uses `ChatOpenAI`, so you can point it at an OpenAI-compatible endpoint without changing the workflow.

For example:

```powershell
$env:OPENAI_API_KEY="your-provider-key"
$env:LANGCHAIN_BASE_URL="https://your-provider.example/v1"
$env:LANGCHAIN_MODEL="your-model"
python examples/langchain_usage.py
```

This is intentionally provider configuration, not workflow configuration.

## 5. Run ClaudeRuntime (Claude Agent SDK)

Set:

```powershell
$env:ANTHROPIC_API_KEY="your-key"
$env:ANTHROPIC_MODEL="claude-sonnet-5-5"
```

Then:

```powershell
python examples/claude_usage.py
```

The model is configurable because provider model names change independently of the workflow specification. The adapter uses the Claude Agent SDK `query()` interface with no built-in tools enabled; the workflow engine remains responsible for orchestration.

## 6. What is actually framework-independent?

The following files do **not** import LangChain or Anthropic:

- `workflow.yaml`
- `workflow_engine/engine.py`
- `workflow_engine/runtime.py`
- `workflow_engine/expression.py`
- `workflow_engine/loader.py`
- `workflow_engine/models.py`

The engine understands generic workflow concepts such as:

- capability
- condition
- state update
- human input
- retry
- terminal

The runtimes implement capabilities.

### Adding a workflow step using an existing primitive

Usually YAML only:

```yaml
- id: explain_result
  type: capability
  capability: result_explanation
```

### Adding a new capability

Add the capability name to YAML and implement it in each runtime that should support it:

```text
workflow.yaml
     |
     +-- capability: chemical_alternative_search

LangChainRuntime  -> LangChain implementation
ClaudeRuntime     -> Claude implementation
MockRuntime       -> deterministic demo implementation
```

The generic engine still does not change.

### Adding a new primitive step type

If you introduce a new workflow primitive such as `parallel`, then the generic engine must learn that primitive. That is an engine change, not a runtime change.

## 7. Why the LLM outputs are plain JSON

The example deliberately avoids provider-specific tool/function calling and provider-specific structured-output APIs. The runtime asks the model for a JSON object and parses it locally.

This keeps the demonstration portable across OpenAI-compatible endpoints and Claude while still making the capability contract explicit.

For production, replace this with a stronger structured-output contract appropriate to each provider and validate every response against a schema.

## 8. Tests

```powershell
pytest -q
```

The test suite exercises the generic engine and mock runtime without network calls.

## 9. Production evolution

This is a runnable reference architecture, not a production-complete orchestration platform. A production implementation should additionally address:

- durable checkpoints and resumable HITL
- execution IDs and persistence
- async execution
- idempotency
- structured logging/tracing
- metrics
- capability discovery and contract validation
- authentication/secrets
- audit/security controls
- stronger schema validation
- provider-specific retry and timeout policies
- workflow schema/version migration

Those concerns can be added without coupling the canonical workflow definition to a particular agent framework.
