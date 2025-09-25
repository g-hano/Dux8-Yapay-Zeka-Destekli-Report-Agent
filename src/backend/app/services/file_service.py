# services/file_service.py
import os
import pandas as pd
from fastapi import UploadFile
from typing import Dict, Any
from dotenv import load_dotenv
from llama_parse import LlamaParse

load_dotenv()

async def save_file(file: UploadFile) -> str:
    """Save file to uploads directory"""
    file_location = f"uploads/{file.filename}"
    
    with open(file_location, "wb+") as file_object:
        file_object.write(file.file.read())
    
    return file_location

async def parse_with_llamaparse(file_path: str) -> str:
    """Parse file to Markdown using LlamaParse (for PDFs)"""
    api_key = os.getenv("LLAMAPARSE_API_KEY")
    if not api_key:
        raise ValueError("LLAMAPARSE_API_KEY not found. Please check your .env file.")
    
    parser = LlamaParse(
        api_key=api_key,
        result_type="markdown"
    )
    
    file_name = os.path.basename(file_path)
    extra_info = {"file_name": file_name}
    
    documents = await parser.aload_data(file_path, extra_info=extra_info)
    
    if not documents or not documents[0].text:
        return "File content could not be read."
    
    return documents[0].text

async def save_markdown(file_path: str, markdown_content: str) -> str:
    """Save markdown content to file"""
    markdown_path = file_path.replace('.pdf', '.md')
    
    with open(markdown_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    return markdown_path

async def process_file(file_path: str, for_rag: bool = False) -> Dict[str, Any]:
    """Process file and return basic information"""
    file_info = {}
    
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if for_rag and file_ext in ['.pdf', '.csv', '.xlsx', '.xls']:
        try:
            markdown_content = await parse_with_llamaparse(file_path)
            markdown_path = await save_markdown(file_path, markdown_content)
            
            file_info = {
                "format": file_ext,
                "markdown_content": markdown_content,
                "markdown_path": markdown_path,
                "char_count": len(markdown_content),
                "word_count": len(markdown_content.split())
            }            
            return file_info
        
        except Exception as e:
            return {
                "format": file_ext,
                "error": str(e),
                "message": f"{file_ext.upper()} processing failed with LlamaParse"
            }

    if file_ext == '.csv':
        df = pd.read_csv(file_path)
        file_info = {
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": df.columns.tolist(),
            "data_types": df.dtypes.astype(str).to_dict(),
            "format": "csv"
        }
    elif file_ext in ['.xlsx', '.xls']:
        df = pd.read_excel(file_path)
        file_info = {
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": df.columns.tolist(),
            "data_types": df.dtypes.astype(str).to_dict(),
            "format": "excel"
        }
    elif file_ext == '.pdf':
        try:
            markdown_content = await parse_with_llamaparse(file_path)
            markdown_path = await save_markdown(file_path, markdown_content)
            
            file_info = {
                "format": "pdf",
                "markdown_content": markdown_content,
                "markdown_path": markdown_path,
                "char_count": len(markdown_content),
                "word_count": len(markdown_content.split())
            }
        except Exception as e:
            file_info = {
                "format": "pdf",
                "error": str(e),
                "message": "PDF processing failed"
            }
    else:
        file_size = os.path.getsize(file_path)
        file_info = {
            "file_size": file_size,
            "file_type": file_ext,
            "message": "File type not supported for detailed analysis"
        }
    
    return file_info