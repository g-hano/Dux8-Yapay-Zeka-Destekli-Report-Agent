# main.py
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
import os
import matplotlib.pyplot as plt
import io
import base64
import polars as pl
import numpy as np
import traceback

from services.file_service import save_file, process_file, parse_with_llamaparse, save_markdown
from services.summary_service import SummaryService
from services.data_processor import DataProcessor
from services.action_service import ActionItemsService
from services.rag_service import add_document_to_rag

from models.file_model import FileResponse
from models.summary_model import SummaryRequest, SummaryResponse as SummaryResponseModel
from models.database import create_tables
from models.schemas import SummaryCreate
from models.schemas import ReportCreate

from api.data import router as data_router
from api.rag import router as rag_router
from api.llamaparse import router as llama_parse_router
from api.structured_parse import router as structured_parse_router
from api.summary import router as summary_router
from api.action import router as action_router
from api.data import router as data_router

from crud.crud import create_report, get_report_by_file_id, create_summary, get_summary_by_report_id
from core.database import get_db

app = FastAPI(title="File Upload and Data Processing Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if not os.path.exists("uploads"):
    os.makedirs("uploads")

@app.post("/upload/", response_model=FileResponse)
async def upload_file(file: UploadFile = File(...), for_rag: bool = False):
    try:
        file_path = await save_file(file)
        file_info = await process_file(file_path, for_rag=for_rag)
        
        return FileResponse(
            filename=file.filename,
            file_type=file.content_type,
            file_path=file_path,
            file_info=file_info
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/api/summary/summarize/", response_model=SummaryResponseModel)
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

@app.post("/api/data/process-data/")
async def process_data(
    file: UploadFile = File(...),
    generate_summary: bool = True,
    generate_actions: bool = True,
    business_context: str = "",
    db: Session = Depends(get_db)
):
    try:
        file_path = await save_file(file)
        
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext == '.pdf':
            try:
                markdown_content = await parse_with_llamaparse(file_path)
                markdown_path = await save_markdown(file_path, markdown_content)
                
                file_id = f"{os.path.splitext(file.filename)[0]}_{int(datetime.now().timestamp())}"
                
                rag_result = add_document_to_rag(file_id, markdown_content)
                
                summary_text = None
                if generate_summary:
                    summary_service = SummaryService()
                    summary_text = summary_service.summarize_document(file_id)
                
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
                
                return {
                    "filename": file.filename,
                    "file_type": file.content_type,
                    "task": "pdf_processing",
                    "markdown_content": markdown_content,
                    "char_count": len(markdown_content),
                    "word_count": len(markdown_content.split()),
                    "file_id": file_id,
                    "summary": summary_text,
                    "report_id": db_report.id
                }
                
            except Exception as e:
                print(f"DEBUG: Traceback: {traceback.format_exc()}")
                raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")
        
        elif file_ext in ['.csv', '.tsv', '.xlsx', '.xls']:
            try:
                processor = DataProcessor()
                df = processor.read_file(file_path)                
                summary = processor.get_data_summary(df)                
                kpis = processor.calculate_kpis(df)                
                trends = processor.identify_trends(df)                

                trends_list = []
                for col, data in trends.items():
                    if isinstance(data, dict):
                        converted = {}
                        for k, v in data.items():
                            if isinstance(v, (np.integer, np.floating)):
                                converted[k] = float(v)
                            else:
                                converted[k] = v
                        trends_list.append({"column": col, **converted})
                trends = trends_list

                sample_data = processor.generate_sample_data(df)
                
                if isinstance(sample_data, list):
                    sample_dict = {}
                    for chunk in sample_data:
                        if isinstance(chunk, dict):
                            for col, vals in chunk.items():
                                if col not in sample_dict:
                                    sample_dict[col] = []
                                if isinstance(vals, list):
                                    sample_dict[col].extend([str(val) if val is not None else "N/A" for val in vals])
                                else:
                                    sample_dict[col].append(str(vals) if vals is not None else "N/A")
                    sample_data = sample_dict
                elif not isinstance(sample_data, dict):
                    sample_data = {}

                action_items_dict = None
                if generate_actions:
                    try:
                        analysis_results = {
                            "summary": summary,
                            "kpis": kpis,
                            "trends": trends,
                            "sample_data": sample_data
                        }
                        
                        action_service = ActionItemsService()
                        
                        if business_context:
                            action_result = action_service.generate_prioritized_actions(
                                analysis_results, business_context
                            )
                        else:
                            action_result = action_service.generate_action_items(analysis_results)
                        
                        action_items_dict = action_result if isinstance(action_result, dict) else action_result.dict()
                        
                    except Exception as e:
                        print(f"DEBUG: Error generating action items: {str(e)}")
                        action_items_dict = {
                            "action_items": [],
                            "summary": "Action items could not be created",
                            "key_insights": [],
                            "note": f"Error: {str(e)}"
                        }
                
                report_data = {
                    "filename": file.filename,
                    "file_type": file.content_type,
                    "file_path": file_path,
                    "data": {
                        "summary": summary,
                        "kpis": kpis,
                        "trends": trends,
                        "sample_data": sample_data,
                        "action_items": action_items_dict
                    }
                }
                
                db_report = create_report(db, ReportCreate(**report_data))
                
                return {
                    "filename": file.filename,
                    "file_type": file.content_type,
                    "task": "data_analysis",
                    "summary": summary,
                    "kpis": kpis,
                    "trends": trends,
                    "sample_data": sample_data,
                    "action_items": action_items_dict,
                    "report_id": db_report.id
                }
                
            except Exception as e:
                print(f"DEBUG: Traceback: {traceback.format_exc()}")
                raise HTTPException(status_code=500, detail=f"Data processing failed: {str(e)}")
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_ext}. Only PDF, CSV, TSV, and Excel files are supported.")
        
    except Exception as e:
        print(f"DEBUG: Error in process_data: {str(e)}")
        import traceback
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


app.include_router(rag_router, prefix="/api", tags=["rag"])
app.include_router(llama_parse_router, prefix="/api", tags=["llama-parse"])
app.include_router(structured_parse_router, prefix="/api", tags=["structured-parse"])
app.include_router(summary_router, prefix="/api", tags=["summary"])
app.include_router(action_router, prefix="/api", tags=["action"])
app.include_router(data_router, prefix="/api", tags=["data"])

@app.post("/api/data/visualize/")
async def visualize_data(
    file: UploadFile = File(...),
    chart_type: str = "line",  # line, bar, scatter
    x_column: str = "",
    y_column: str = ""
):
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

        if not x_column:
            x_column = df.columns[0]
        if not y_column:
            for col in df.columns:
                if df[col].dtype in [pl.Float32, pl.Float64, pl.Int8, pl.Int16, pl.Int32, pl.Int64]:
                    y_column = col
                    print(f"DEBUG: Found numeric column for y: {y_column}")
                    break
        
        if not y_column:
            raise ValueError("No numeric column found for visualization")
        
        # Create chart
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
        
        plt.savefig(file_path, format='png', dpi=300, bbox_inches='tight')
        
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


@app.on_event("startup")
async def startup_event():
    create_tables()
    
    print("DEBUG: Registered routes:")
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            print(f"  {route.methods} {route.path}")

@app.get("/")
def root():
    return {"message": "File Upload and Data Processing API is running"}

if __name__ == "__main__":
    print("DEBUG: Starting server")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)