
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

from app.llm.deepseek import DeepSeek_LLM

from embeddings import get_embedding
from Chromadb import get_Chroma_db
# Chroma DB, embeddings 创建或加载 已有或未存在的 Chroma DB collection
embeddings = get_embedding()
db = get_Chroma_db(embeddings)


# 检索查询,并且返回
def retrieve_query():
    docs_find=RunnableLambda(db.similarity_search).bind(k=2)
    return docs_find


message='''
仅仅使用下面的上下文里面的标准答案来评估用户模拟面试的质量,而你将扮演一个面试官
{question}
上下文:
{context}

'''
prompt_template=ChatPromptTemplate([('human',message)])

chain = {"question":RunnablePassthrough(),
         "context":retrieve_query()}|prompt_template|DeepSeek_LLM
response = chain.invoke("自动装箱是将基本数据类型自动转换为对应的包装类对象,而自动拆箱是将包装类对象人为主动转换为基本数据类型")
print(response.content)
