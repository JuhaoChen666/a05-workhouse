import os
from dotenv import load_dotenv
from langchain_community.embeddings import DashScopeEmbeddings
from app.RAG.document import process_markdown

# 使用原生 OpenAI SDK 测试
load_dotenv()

def get_embedding():
    embeddings = DashScopeEmbeddings(
        model="text-embedding-v3",
        dashscope_api_key=os.getenv("DASHSCOPE_API_KEY")
    )
    return embeddings



if __name__ == "__main__":
    embeddings = get_embedding()
    print(embeddings.embed_query("这是一个测试文本"))



