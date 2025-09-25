from pydantic import BaseModel
from typing import Dict, Any

class FileResponse(BaseModel):
    filename: str
    file_type: str
    file_path: str
    file_info: Dict[str, Any]
    
    class Config:
        from_attributes = True

class MarkdownResponse(BaseModel):
    file_id: str
    filename: str
    markdown_content: str
    char_count: int
    word_count: int
    markdown_path: str
    
    class Config:
        from_attributes = True