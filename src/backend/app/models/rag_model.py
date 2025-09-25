from pydantic import BaseModel
from typing import List, Dict, Any

class AddDocumentRequest(BaseModel):
    file_id: str
    text: str

class AddDocumentResponse(BaseModel):
    message: str

class QueryRequest(BaseModel):
    file_id: str
    query: str

class QueryResponse(BaseModel):
    query: str
    answer: str
    sources: List[Dict[str, Any]]
    
    class Config:
        from_attributes = True