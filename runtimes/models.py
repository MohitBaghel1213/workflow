import os
from langchain_openai import ChatOpenAI
from langchain.chat_models import init_chat_model

# model = init_chat_model("ollama:qwen3:1.7b")
# model = ChatOpenAI(model="apodex/apodex-1.1-mini:free", base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"])
model = ChatOpenAI(model="openrouter/free", base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"])