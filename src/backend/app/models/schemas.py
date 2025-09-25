# models/schemas.py
from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime

# Summary schemas
class SummaryBase(BaseModel):
    report_id: int
    summary_text: str

class SummaryCreate(SummaryBase):
    pass

class SummaryResponse(SummaryBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Report schemas
class ReportBase(BaseModel):
    filename: str
    file_type: str
    file_path: str
    data: Dict[str, Any]

class ReportCreate(ReportBase):
    pass

class ReportResponse(ReportBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True