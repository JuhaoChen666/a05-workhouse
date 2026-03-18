import os
from openai import OpenAI
from langchain_chroma import Chroma
# 使用原生 OpenAI SDK 测试
client = OpenAI(
    api_key="sk-cc10457e8f7f46138bbd665b8eb31ed1",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

text = "这是一个测试文本"
response = client.embeddings.create(
    model="text-embedding-v3",
    input=text
)

print(response.data[0].embedding)
print(len(response.data[0].embedding))

