from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
import os
import polars as pl
import matplotlib.pyplot as plt
import base64
import io
import os
from datetime import datetime
from sqlalchemy.orm import Session
import traceback

from services.file_service import save_file, parse_with_llamaparse, save_markdown
from services.data_processor import DataProcessor
from services.rag_service import add_document_to_rag
from services.action_service import ActionItemsService

from models.data_model import DataProcessingResponse
from models.file_model import MarkdownResponse
from models.schemas import ReportCreate
from models.action_model import ActionItemsResponse, ActionItem

from core.database import get_db
from crud.crud import create_report

router = APIRouter()

action_service = ActionItemsService()

@router.post("/process-data/", response_model=DataProcessingResponse)
async def process_data(
    file: UploadFile = File(...),
    generate_actions: bool = True,
    business_context: str = ""
):
    try:
        file_path = await save_file(file)
        
        processor = DataProcessor()

        df = processor.read_file(file_path)
        
        summary = processor.get_data_summary(df)
        
        kpis = processor.calculate_kpis(df)
        
        trends = processor.identify_trends(df)
        
        sample_data = processor.generate_sample_data(df)
        
        response_data = {
            "filename": file.filename,
            "file_type": file.content_type,
            "summary": summary,
            "kpis": kpis,
            "trends": trends,
            "sample_data": sample_data
        }
        
        if generate_actions:
            try:
                analysis_results = {
                    "summary": summary,
                    "kpis": kpis,
                    "trends": trends,
                    "sample_data": sample_data
                }
                
                if business_context:
                    action_result = action_service.generate_prioritized_actions(
                        analysis_results, business_context
                    )
                else:
                    action_result = action_service.generate_action_items(analysis_results)
                
                action_items = []
                for item in action_result.get('action_items', []):
                    action_items.append(ActionItem(**item))
                
                action_items_response = ActionItemsResponse(
                    action_items=action_items,
                    summary=action_result.get('summary', ''),
                    key_insights=action_result.get('key_insights', []),
                    note=action_result.get('note')
                )
                
                response_data["action_items"] = action_items_response
                
            except Exception as e:
                response_data["action_items"] = ActionItemsResponse(
                    action_items=[],
                    summary="Action items could not be created",
                    key_insights=[],
                    note=f"Error: {str(e)}"
                )
        
        return response_data
        
    except Exception as e:
        print(f"DEBUG: Error in process_data: {str(e)}")
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Data processing failed: {str(e)}")

@router.post("/generate-actions-from-file/")
async def generate_actions_from_file(
    file: UploadFile = File(...),
    business_context: str = ""
):
    try:
        file_path = await save_file(file)
        processor = DataProcessor()
        df = processor.read_file(file_path)
        
        analysis_results = {
            "summary": processor.get_data_summary(df),
            "kpis": processor.calculate_kpis(df),
            "trends": processor.identify_trends(df),
            "sample_data": processor.generate_sample_data(df)
        }
        
        if business_context:
            result = action_service.generate_prioritized_actions(
                analysis_results, business_context
            )
        else:
            result = action_service.generate_action_items(analysis_results)
        
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
        raise HTTPException(status_code=500, detail=f"Action generation failed: {str(e)}")

@router.post("/visualize/")
async def visualize_data(
    file: UploadFile = File(...),
    chart_type: str = "line",  # line, bar, scatter
    x_column: str = "",
    y_column: str = ""
):
    """Create visualizations from structured data files (Excel, CSV, TSV)"""
    try:
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ['.csv', '.xlsx', '.xls', '.tsv']:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type: {file_ext}. Only CSV, Excel, and TSV files are supported for visualization"
            )
    
        file_path = await save_file(file)
        
        processor = DataProcessor()
        df = processor.read_file(file_path)

        # Set default columns
        if not x_column:
            x_column = df.columns[0]
        if not y_column:
            for col in df.columns:
                if df[col].dtype in [pl.Float32, pl.Float64, pl.Int8, pl.Int16, pl.Int32, pl.Int64]:
                    y_column = col
                    break
        
        if not y_column:
            raise ValueError("No numeric column found for visualization")
        
        plt.figure(figsize=(10, 6))
        if chart_type == "line":
            plt.plot(df[x_column], df[y_column], marker='o')
        elif chart_type == "bar":
            plt.bar(df[x_column], df[y_column])
        elif chart_type == "scatter":
            plt.scatter(df[x_column], df[y_column])
        else:
            raise ValueError(f"Invalid chart type: {chart_type}")
        
        plt.title(f"{y_column} by {x_column}")
        plt.xlabel(x_column)
        plt.ylabel(y_column)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        vis_folder = "uploads/visualizations"
        if not os.path.exists(vis_folder):
            os.makedirs(vis_folder)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename.replace('.', '_')}_{chart_type}.png"
        file_path = os.path.join(vis_folder, filename)
        
        # Save chart to file
        plt.savefig(file_path, format='png', dpi=300, bbox_inches='tight')
        
        # Convert chart to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close()
        
        return {
            "filename": file.filename,
            "chart_type": chart_type,
            "x_column": x_column,
            "y_column": y_column,
            "image": f"data:image/png;base64,{image_base64}",
            "saved_path": file_path,
            "saved_filename": filename
        }
    except HTTPException as http_exc:
        print(f"DEBUG: HTTPException raised: {http_exc.detail}")
        raise
    except Exception as e:
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Visualization failed: {str(e)}")

@router.post("/parse/", response_model=MarkdownResponse)
async def parse_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        file_path = await save_file(file)
        
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files can be parsed")
        
        markdown_content = await parse_with_llamaparse(file_path)
        markdown_path = await save_markdown(file_path, markdown_content)
        
        file_id = f"{os.path.splitext(file.filename)[0]}_{int(datetime.now().timestamp())}"

        add_document_to_rag(file_id, markdown_content)
        
        report_data = {
            "filename": file.filename,
            "file_type": file.content_type,
            "file_path": file_path,
            "data": {
                "markdown_content": markdown_content,
                "char_count": len(markdown_content),
                "word_count": len(markdown_content.split()),
                "file_id": file_id
            }
        }
        
        db_report = create_report(db, ReportCreate(**report_data))
        
        response = MarkdownResponse(
            filename=file.filename,
            markdown_content=markdown_content,
            char_count=len(markdown_content),
            word_count=len(markdown_content.split()),
            file_id=file_id,
            markdown_path=markdown_path
        )
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")

