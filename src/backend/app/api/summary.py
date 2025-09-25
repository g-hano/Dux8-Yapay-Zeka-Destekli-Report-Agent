# api/summary.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import traceback

from services.summary_service import SummaryService
from models.summary_model import SummaryRequest, SummaryResponse as SummaryResponseModel
from models.schemas import SummaryCreate
from core.database import get_db
from crud.crud import create_summary, get_summary_by_report_id, get_report_by_file_id

router = APIRouter()

@router.post("/summarize/", response_model=SummaryResponseModel)
async def summarize_document(
    request: SummaryRequest,
    db: Session = Depends(get_db)
):
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
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")