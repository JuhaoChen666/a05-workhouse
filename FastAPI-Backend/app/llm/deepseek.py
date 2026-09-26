from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

DeepSeek_LLM=ChatOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    model_name=os.getenv("DEEPSEEK_MODEL", "deepseek-flash"),
    base_url="https://api.deepseek.com",
    temperature=0.7)


