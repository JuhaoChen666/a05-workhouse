import os

from langchain_community.embeddings import DashScopeEmbeddings
from openai import OpenAI
from langchain_chroma import Chroma
# 使用原生 OpenAI SDK 测试


def get_embedding():
    embeddings = DashScopeEmbeddings(
        model="text-embedding-v3",
        dashscope_api_key=os.getenv("DASHSCOPE_API_KEY")
    )
    return embeddings


if __name__ == "__main__":
    embeddings = get_embedding()
    print(embeddings.embed_query("这是一个测试文本"))



