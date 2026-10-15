"""Run the basic composed workflow using LangChain."""
from main import build_engine
from runtimes.langchain_runtime import LangChainRuntime
from runtimes.models import model

if __name__ == "__main__":
    engine = build_engine("advanced", LangChainRuntime(model))
    result = engine.run({"user_prompt": input("Initial prompt: ").strip()})
    print(result)
