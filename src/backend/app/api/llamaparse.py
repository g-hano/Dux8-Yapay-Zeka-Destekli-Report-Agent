# api/llama_parse.py
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
import os
from datetime import datetime

from services.file_service import save_file, parse_with_llamaparse, save_markdown
from services.rag_service import add_document_to_rag
from services.summary_service import SummaryService
from models.file_model import MarkdownResponse
from models.schemas import ReportCreate, SummaryCreate
from models.summary_model import SummaryRequest, SummaryResponse as SummaryResponseModel
from core.database import get_db
from crud.crud import create_report, get_report_by_file_id, create_summary, get_summary_by_report_id

router = APIRouter()

@router.post("/llama-parse/", response_model=MarkdownResponse)
async def parse_pdf(
    file: UploadFile = File(...),
    generate_summary: bool = True,
    max_length: int = 500,
    db: Session = Depends(get_db)
):
    try:
        file_path = await save_file(file)
        markdown_content = await parse_with_llamaparse(file_path)
        markdown_path = await save_markdown(file_path, markdown_content)
        
        file_id = f"{os.path.splitext(file.filename)[0]}_{int(datetime.now().timestamp())}"
        
        add_document_to_rag(file_id, markdown_content)
        
        summary_text = None
        if generate_summary:
            summary_service = SummaryService()
            summary_text = summary_service.summarize_document(file_id, max_length)
        
        report_data = {
            "filename": file.filename,
            "file_type": file.content_type,
            "file_path": file_path,
            "data": {
                "markdown_content": markdown_content,
                "char_count": len(markdown_content),
                "word_count": len(markdown_content.split()),
                "file_id": file_id,
                "summary": summary_text
            }
        }
        
        db_report = create_report(db, ReportCreate(**report_data))
        
        if generate_summary and summary_text:
            summary_create = SummaryCreate(
                report_id=db_report.id,
                summary_text=summary_text
            )
            create_summary(db, summary_create)
        
        return MarkdownResponse(
            filename=file.filename,
            markdown_content=markdown_content,
            char_count=len(markdown_content),
            word_count=len(markdown_content.split()),
            file_id=file_id,
            markdown_path=markdown_path,
            summary=summary_text,
            report_id=db_report.id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF parsing failed: {str(e)}")

@router.post("/llama-parse/summarize/", response_model=SummaryResponseModel)
async def summarize_parsed_pdf(
    request: SummaryRequest,
    db: Session = Depends(get_db)
):
    """Generate a summary for a previously parsed PDF document"""
    try:
        report = get_report_by_file_id(db, request.file_id)
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        existing_summary = get_summary_by_report_id(db, report.id)
        if existing_summary:
            return SummaryResponseModel(
                file_id=request.file_id,
                summary=existing_summary.summary_text
            )
        
        summary_service = SummaryService()
        summary_text = summary_service.summarize_document(request.file_id, request.max_length)
        
        summary_create = SummaryCreate(
            report_id=report.id,
            summary_text=summary_text
        )
        db_summary = create_summary(db, summary_create)
        
        return SummaryResponseModel(
            file_id=request.file_id,
            summary=db_summary.summary_text
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")