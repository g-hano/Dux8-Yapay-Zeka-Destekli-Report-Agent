from pydantic import BaseModel
from typing import Dict, Any, List, Optional

class DataSummary(BaseModel):
    shape: List[int]
    columns: List[str]
    dtypes: Dict[str, str]
    null_counts: Dict[str, int]
    memory_usage: float

class KPIResponse(BaseModel):
    statistics: Optional[Dict[str, Any]] = None
    categorical: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

class TrendResponse(BaseModel):
    trend: str
    correlation: Optional[float] = None
    first_half_mean: Optional[float] = None
    second_half_mean: Optional[float] = None

class DataProcessingResponse(BaseModel):
    filename: str
    file_type: str
    summary: Dict[str, Any]
    kpis: Dict[str, Any]
    trends: List[Dict[str, Any]]
    sample_data: Dict[str, Any]
    action_items: Optional[Dict[str, Any]] = None
    rag_file_id: Optional[str] = None