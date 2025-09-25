from fastapi import APIRouter, Depends, HTTPException
from services.rag_service import RAGService
from models.rag_model import (
    AddDocumentRequest, AddDocumentResponse,
    QueryRequest, QueryResponse
)

router = APIRouter()

rag_service = RAGService()

@router.post("/add-document/", response_model=AddDocumentResponse)
async def add_document(request: AddDocumentRequest):
    try:
        message = rag_service.add_document(request.file_id, request.text)
        return AddDocumentResponse(message=message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Doküman eklenemedi: {str(e)}")

@router.post("/query/", response_model=QueryResponse)
async def query_document(request: QueryRequest):
    try:
        response = rag_service.query(request.file_id, request.query)
        print(response)
        return QueryResponse(**response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sorgu yapılamadı: {str(e)}")

@router.delete("/document/{file_id}")
async def delete_document(file_id: str):
    try:
        message = rag_service.delete_document(file_id)
        return {"message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Doküman silinemedi: {str(e)}")