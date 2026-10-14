"""Run the basic composed workflow using Claude Agent SDK."""
from main import build_engine
from runtimes.claude_runtime import ClaudeRuntime

if __name__ == "__main__":
    engine = build_engine("basic", ClaudeRuntime())
    result = engine.run({"user_prompt": input("Initial prompt: ").strip()})
    print(result)
