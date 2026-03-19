import chromadb

from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings

from langchain_core.documents import Document
from multipart import file_path
from embeddings import get_embedding


from document import process_markdown

from openai import OpenAI


score_measures=[
    "default"
    "cosine",
    "l2"
    "ip"
]

def get_Chroma_db(embeddings):

    db = Chroma(
        collection_name="test_collection",
        embedding_function=embeddings,
        persist_directory="./chroma_db",
        collection_metadata={"hnsw:space":'l2'}
        )
    return db

if __name__ == "__main__":
    embeddings = get_embedding()
    db = get_Chroma_db(embeddings)
    print(db._collection_name)
