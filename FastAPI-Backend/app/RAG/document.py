from langchain_community.document_loaders import DirectoryLoader, UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from langchain_core.documents import Document



# Markdown 文件加载器
'''
loader = UnstructuredMarkdownLoader("D:/a05-workhouse/测试文档切分题库.md")
documents = loader.load()
print(documents)
print('-'*100)
'''
'''直接切割md文件跳过文档加载器'''
#文档切分器
def process_markdown(file_path):
    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    # 定义切分规则
    headers_to_split_on=[
        ("#","岗位知识库名"),
        ("##","大类"),
        ("###","分类"),
        ("####","小类"),
    ]
    markdown_splitter=MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False
    )

    # 执行切分
    splits=markdown_splitter.split_text(content)

    # 4. 转换为 LangChain Document 格式
    documents = []
    for i, split in enumerate(splits):
        doc = Document(
            page_content=split.page_content,
            metadata={
                **split.metadata,
                "source": file_path,
                "chunk_id": i
            }
        )
        documents.append(doc)

    return documents

# 测试
if __name__ == "__main__":
    file_path = "D:/a05-workhouse/测试文档切分题库.md"
    docs = process_markdown(file_path)

    print(f"\n共生成 {len(docs)} 个文档块")
    for i, doc in enumerate(docs[:3]):  # 显示前 3 个
        print(f"\n--- 块 {i+1} ---")
        print(f"元数据：{doc.metadata}")
        print(f"内容预览：{doc.page_content[:100]}...")

