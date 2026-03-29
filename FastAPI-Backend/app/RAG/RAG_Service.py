import os

from sympy.strategies.core import switch

os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGCHAIN_TRACING"] = "false"
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

from app.llm.deepseek import DeepSeek_LLM

from app.RAG.embeddings import get_embedding
from app.RAG.Chromadb import get_Chroma_db

# Chroma DB, embeddings 创建或加载 已有或未存在的 Chroma DB collection
embeddings = get_embedding()


# 输入岗位名称
collection_name = input("请输入岗位名称: ")




# 创建或加载对应岗位的知识库和问题库
db_kb = get_Chroma_db(embeddings, collection_name+"_kb")
db_qb = get_Chroma_db(embeddings, collection_name+"_qb")

print(f"\n知识库 '{collection_name}_kb' 中的文档数量: {db_kb._collection.count()}")
print(f"问题库 '{collection_name}_qb' 中的文档数量: {db_qb._collection.count()}")

def create_retriever(db, query_builder):
    """创建一个检索器，根据输入构建查询并检索"""
    def retriever(inputs):
        query = query_builder(inputs)
        docs = db.similarity_search(query, k=2)
        return "\n".join([doc.page_content for doc in docs])
    return RunnableLambda(retriever)

# 定义查询构建函数
def build_kb_query(inputs):
    return f"简历: {inputs['resume']}\n岗位: {inputs['position']}\n用户回答: {inputs['user_answer']}"

def build_qb_query(inputs):
    return f"简历: {inputs['resume']}\n岗位: {inputs['position']}"

# 创建检索器
knowledge_retriever = create_retriever(db_kb, build_kb_query)
question_retriever = create_retriever(db_qb, build_qb_query)

message='''
仅仅使用下面的知识库里面的标准答案以及问题库里的问题,而你将扮演一个面试官,假装你看过他的简历,并根据简历内容和
他的经验及面试岗位来向他提出问题,问题应该根据从简单到难,问题库里面有难度系数,难度系数越大越难,并在他做出回答后给出评价其回答质量,给他的面试进行评分.
简历:
{resume}
岗位信息:
{position}
用户回答:
{user_answer}
知识库:
{knowledge_collection}
问题库:
{question_collection}


'''
prompt_template=ChatPromptTemplate([('human',message)])

chain = {"resume":RunnablePassthrough(),
         "position":RunnablePassthrough(),
         "user_answer":RunnablePassthrough(),
         "knowledge_collection":knowledge_retriever,
         "question_collection":question_retriever
         }|prompt_template|DeepSeek_LLM
response = chain.invoke({
    "resume": "候选人张三，3年Android开发经验，熟悉Java/Kotlin，有电商项目经验...",
    "position": "移动端开发工程师(Android)",
    "user_answer": input("请输入你的回答: ")
                         })
print(response.content)
