# Framework-Independent Chemical Alternative Workflow

This project is a runnable reference implementation of the chemical/material substitution workflow described in `workflows/chemical_alternative.yaml`. The workflow engine is declarative; domain operations are registered capabilities; tool implementations are registered separately; and candidate research uses a shared tool-calling agent runtime.

> **Demo/data warning:** The knowledge graph, web search, inferred property values, candidate data, and match scores in this package are mocked. The Ashby equation is an illustrative placeholder. This is runnable architecture/demo code, not a validated engineering recommendation system. Connect vetted material databases, live search, domain-specific equation generation, screening rules, authentication, persistence, observability, and human approval before production use.

## Run

Python 3.11+ recommended.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python main.py --demo
```

Interactive mode:

```bash
python main.py
```

Or pass a prompt directly:

```bash
python main.py --prompt "material=ExamplePolymer, product=toothbrush, functional_requirement=durable, reason_for_substitution=reduce cost"
```

Run tests:

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Workflow files

- `workflows/chemical_alternative.yaml`: main workflow; extracts six contract slots, enforces mandatory material, asks for confirmation, resolves missing values, builds application context, creates/ confirms Ashby formulation, generates an equation placeholder, resolves baseline/candidate properties, searches candidates, screens, and ranks.
- `workflows/property-resolution.yaml`: reusable ordered fallback sub-workflow: knowledge graph → web search → LLM inference → ask user. It is reused for missing slots, baseline properties, and candidate properties.
- Previous demo workflows have been removed from the active workflow registry.

## Architecture

- `WorkflowEngine`: executes the workflow graph and owns execution limits/state.
- `StepHandlerRegistry`: dispatches generic step types (`capability`, `condition`, `human_input`, `state_update`, `workflow`, `terminal`).
- `CapabilityRegistry` / `CapabilityExecutor`: resolves capability IDs and injects shared services.
- `ChemicalWorkflowCapability`: local demo implementations for domain operations. Replace source and domain methods with real implementations.
- `ToolManager`: tool registry and executor. Tools are registered once with descriptions and schemas.
- `ToolCallingAgentRuntime`: shared model → tool call → tool result → model loop. The `search_candidate_materials` capability reuses it.
- `MockToolCallingModel`: deterministic scripted model used for offline execution. It demonstrates the tool-call protocol; it does not perform genuine LLM reasoning.

## Add a tool

1. Implement an object exposing `execute(inputs, context)`.
2. Register it in `build_tool_manager()` with a stable ID, description, and JSON input schema.
3. Add the tool ID to the capability's allowlist.
4. For a real model, implement the `ToolCallingModel.next_action(messages, tools)` contract for your provider, preserving provider tool-call IDs and result formats as needed.

## Replace mock integrations

Replace `resolve_from_knowledge_graph`, `resolve_from_web`, and `resolve_with_llm` in `workflow_engine/capabilities/chemical.py` with service clients. A source should return `found: true` only when it has sufficient evidence for the requested property, with provenance/citations. Do not use unverified LLM guesses as material-property facts. The final screening/ranking stages should use deterministic constraints and validated material-index calculations; the LLM should summarize evidence and uncertainty, not certify equivalence.

## Input contract

The workflow accepts:

```json
{
  "user_prompt": "material=ExamplePolymer, product=toothbrush, functional_requirement=durable, reason_for_substitution=reduce cost",
  "files": [],
  "request_id": "optional-request-id"
}
```

`files` currently accepts objects containing extracted `text`/`content` or a `name`. PDF parsing/OCR and secure file storage are not implemented in this demo; pass extracted text or implement a file-ingestion capability.

## Known limitations before production

- No durable checkpoint/resume or persisted human-input sessions.
- No authentication, authorization, tenant isolation, rate limits, or secrets management beyond normal environment configuration.
- No real KG/web connector or PDF parser/OCR.
- No verified material properties, safety/compliance assessment, or real Ashby equation solver.
- The demo human input is synchronous. A production service should pause and resume executions through a durable interaction store.
- Tool outputs are mocked; all scores and candidate rankings are illustrative.
