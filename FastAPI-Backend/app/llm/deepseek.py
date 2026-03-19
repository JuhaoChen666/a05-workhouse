from langchain_openai import ChatOpenAI



DeepSeek_LLM=ChatOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    model_name="deepseek-chat",
    base_url="https://api.deepseek.com/v1",
    temperature=0.7)


