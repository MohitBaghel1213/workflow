# Reusable agent + tool registry walkthrough

## Run the complete mock demonstration

```bash
pip install -r requirements.txt
python main.py --workflow advanced --demo
```

No credentials or network access are required. The demo uses hardcoded candidate data and a deterministic mock tool-calling model.

## Runtime call path

1. `WorkflowEngine` reaches the `find_chemical_alternatives` YAML step (`type: capability`).
2. `CapabilityStepHandler` reads the business capability definition from workflow YAML. Its `implementation: agent` maps the business capability to the single reusable `AgentCapability` implementation.
3. `CapabilityExecutor` injects shared services (`tool_manager` and `agent_runtime`) into the execution context. This prevents the previous missing-service error.
4. `AgentCapability` reads instructions, tool IDs, and iteration limit from YAML and delegates to `ToolCallingAgentRuntime`. It contains no agent loop.
5. `ToolCallingAgentRuntime` retrieves schemas from `ToolManager`, gives those schemas to the model, validates each requested tool against the configured allowlist, executes it through `ToolManager`, and sends results back to the model.
6. The loop repeats until the model returns a final response or the iteration limit is reached. The result includes a tool trace.
7. The workflow engine stores the output and reaches the terminal step.

## Add a new agentic capability

Add another entry under `workflow.capabilities.definitions` in your workflow YAML. Choose `implementation: agent`, provide instructions, a list of registered tool IDs, and `max_iterations`. The same `AgentCapability` and `ToolCallingAgentRuntime` are reused; no new `execute()` method or agent loop is needed.

```yaml
capabilities:
  allowed: [find_chemical_alternatives, market_research]
  definitions:
    market_research:
      implementation: agent
      required_inputs: [topic]
      config:
        instructions: Research the supplied topic using available tools.
        tools: [web_search, market_data_search]
        max_iterations: 6
```

Register each concrete tool once in `build_tool_manager()` (or your application bootstrap). A tool needs an implementation, description, and input schema. Only tools listed in the capability's YAML config are exposed to its model.

## Key files

- `workflows/chemical_alternative_advanced.yaml`: business capability definition and agent configuration.
- `workflow_engine/capabilities/tool_calling.py`: generic `AgentCapability` wrapper; no loop.
- `workflow_engine/agent_runtime.py`: one reusable model/tool-calling loop.
- `workflow_engine/capabilities/executor.py`: maps a business capability ID to a registered implementation and injects shared services.
- `workflow_engine/bootstrap.py`: registers implementation types and mock tools; supplies a working default agent runtime.
- `tools/manager.py`: tool registry, schema exposure, and tool dispatch.
- `runtimes/mock_tool_calling_model.py`: deterministic mock model used for no-key demonstrations.

## Replacing the mock with a real LLM

Implement `ToolCallingModel.next_action(messages, tools)` using your provider's native tool-calling API. Convert provider responses into either:

```python
{"type": "tool_call", "name": "tool_id", "arguments": {}}
```

or:

```python
{"type": "final", "content": "...", "candidates": []}
```

The loop, capability, registry, allowlist enforcement, and workflow YAML remain unchanged. The included mock model calls tools in order and is not an intelligent planner. All candidate data and scores are fabricated; do not use them as evidence of chemical suitability.
