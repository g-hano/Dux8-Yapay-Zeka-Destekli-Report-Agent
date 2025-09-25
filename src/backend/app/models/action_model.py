from pydantic import BaseModel
from typing import List, Optional

class ActionItem(BaseModel):
    priority: str  # high, medium, low
    category: str  # performance, optimization, risk, opportunity, data_quality
    title: str
    description: str
    expected_impact: str
    timeline: str
    responsible: str

class ActionItemsRequest(BaseModel):
    file_data: dict  # Analysis results (summary, kpis, trends, sample_data)
    business_context: Optional[str] = ""

class ActionItemsResponse(BaseModel):
    action_items: List[ActionItem]
    summary: str
    key_insights: List[str]
    note: Optional[str] = None
    
    class Config:
        from_attributes = True

class EnhancedDataProcessingResponse(BaseModel):
    filename: str
    file_type: str
    summary: dict
    kpis: dict
    trends: dict
    sample_data: List[dict]
    action_items: ActionItemsResponse
    
    class Config:
        from_attributes = True