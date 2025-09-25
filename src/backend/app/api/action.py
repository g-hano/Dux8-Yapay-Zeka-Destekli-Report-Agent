from fastapi import APIRouter, HTTPException
from services.action_service import ActionItemsService
from models.action_model import (
    ActionItemsRequest, 
    ActionItemsResponse,
    ActionItem
)

router = APIRouter()

# Global Action Items service
action_service = ActionItemsService()

@router.post("/generate-actions/", response_model=ActionItemsResponse)
async def generate_action_items(request: ActionItemsRequest):
    """Generate action items from analysis results"""
    try:
        if request.business_context:
            result = action_service.generate_prioritized_actions(
                request.file_data, 
                request.business_context
            )
        else:
            result = action_service.generate_action_items(request.file_data)
        
        action_items = []
        for item in result.get('action_items', []):
            action_items.append(ActionItem(**item))
        
        return ActionItemsResponse(
            action_items=action_items,
            summary=result.get('summary', ''),
            key_insights=result.get('key_insights', []),
            note=result.get('note')
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Action items could not be created: {str(e)}")

@router.post("/analyze-and-generate-actions/")
async def analyze_and_generate_actions(
    analysis_results: dict,
    business_context: str = ""
):
    """Quick analysis + action items (in a single endpoint)"""
    try:
        request = ActionItemsRequest(
            file_data=analysis_results,
            business_context=business_context
        )
        
        return await generate_action_items(request)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis and action items failed: {str(e)}")