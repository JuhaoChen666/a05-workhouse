import pypdf
import os
from typing import Optional

def extract_text_from_pdf(pdf_path: str) -> Optional[str]:
    """
    用 pypdf 从 PDF 文件提取文本
    """
    if not os.path.exists(pdf_path):
        return None
    
    try:
        text = ""
        with open(pdf_path, 'rb') as file:
            reader = pypdf.PdfReader(file)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        return text.strip() if text else None
    except Exception as e:
        print(f"提取 PDF 文本出错: {str(e)}")
        return None
