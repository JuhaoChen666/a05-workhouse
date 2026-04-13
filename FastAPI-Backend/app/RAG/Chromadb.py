from langchain_chroma import Chroma

from app.RAG.document import process_markdown
from app.RAG.embeddings import get_embedding


score_measures=[
    "default"
    "cosine",
    "l2"
    "ip"
]
def get_Chroma_db(embeddings, collection_name):
    """Get Chroma database instance."""
    db = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory="./chroma_db",
        collection_metadata={"hnsw:space":'l2'}
        )
    return db


if __name__ == "__main__":
    documents = process_markdown("D:/a05-workhouse/运维工程师_DevOps_问题库.md")
    embeddings = get_embedding()
    db = get_Chroma_db(embeddings, collection_name="devops_engineer_qb")
    ids = db.add_documents(documents)
    print(ids)
    print('-' * 100)
    print("Import Collection Success")
    db = get_Chroma_db(embeddings, collection_name="devops_engineer_qb")
    print(db._collection_name)
