# api/structured_parse.py
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
import os
import numpy as np
from datetime import datetime

from services.file_service import save_file, process_file
from services.data_processor import DataProcessor
from services.action_service import ActionItemsService
from services.rag_service import add_document_to_rag
from models.data_model import DataProcessingResponse
from core.database import get_db
from crud.crud import create_report
from models.schemas import ReportCreate

router = APIRouter()

@router.post("/parse/", response_model=DataProcessingResponse)
async def parse_structured_data(
    file: UploadFile = File(...),
    generate_actions: bool = True,
    business_context: str = "",
    add_to_rag: bool = True,
    db: Session = Depends(get_db)
):
    """Parse structured data files (Excel, CSV, TSV) for Trend & KPIs, Action-Items, and Visualization"""
    try:
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ['.csv', '.xlsx', '.xls', '.tsv']:
            raise HTTPException(
                status_code=400, 
                detail="Only CSV, Excel, and TSV files are supported by this endpoint"
            )
        
        file_path = await save_file(file)
        rag_file_id = None
        markdown_content = None
        if add_to_rag:
            file_info = await process_file(file_path, for_rag=True)
            if "markdown_content" in file_info:
                markdown_content = file_info["markdown_content"]
                
                rag_file_id = f"{os.path.splitext(file.filename)[0]}_kpi_{int(datetime.now().timestamp())}"
                
                add_document_to_rag(rag_file_id, markdown_content)

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

        if add_to_rag and rag_file_id and markdown_content:
            report_data["data"]["rag_file_id"] = rag_file_id
            report_data["data"]["markdown_report"] = markdown_content
            
            db_report.data = report_data["data"]
            db.commit()

        return DataProcessingResponse(
            filename=file.filename,
            file_type=file.content_type,
            summary=summary,
            kpis=kpis,
            trends=trends,
            sample_data=sample_data,
            action_items=action_items_dict,
            report_id=db_report.id,
            rag_file_id=rag_file_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data processing failed: {str(e)}")
    

def create_kpi_markdown_report(filename, summary, kpis, trends, action_items=None):
    """Create a markdown report from KPI analysis results"""
    report = f"# KPI Analysis Report: {filename}\n\n"
    
    # Add summary section
    report += "## Data Summary\n\n"
    report += f"- **Total Rows**: {summary.get('rows', 'N/A')}\n"
    report += f"- **Total Columns**: {summary.get('columns', 'N/A')}\n"
    report += f"- **Column Names**: {', '.join(summary.get('column_names', []))}\n\n"
    
    # Add KPIs section
    report += "## Key Performance Indicators (KPIs)\n\n"
    
    # Add statistics
    if 'statistics' in kpis:
        report += "### Statistical Summary\n\n"
        for col, stats in kpis['statistics'].items():
            if len(stats) >= 5:  # min, max, mean, median, std
                report += f"#### {col}\n"
                report += f"- **Minimum**: {stats[0]}\n"
                report += f"- **Maximum**: {stats[1]}\n"
                report += f"- **Mean**: {stats[2]}\n"
                report += f"- **Median**: {stats[3]}\n"
                report += f"- **Standard Deviation**: {stats[4]}\n\n"
    
    if 'categorical' in kpis:
        report += "### Categorical Analysis\n\n"
        for col, data in kpis['categorical'].items():
            report += f"#### {col}\n"
            report += f"- **Unique Values**: {data.get('unique_count', 'N/A')}\n"
            if 'most_common' in data:
                report += f"- **Most Common Value**: {data['most_common']}\n"
            report += "\n"
    
    # Add trends section
    report += "## Trend Analysis\n\n"
    for trend in trends:
        col = trend.get('column', 'Unknown')
        direction = trend.get('trend', 'unknown')
        correlation = trend.get('correlation', 0)
        
        # Add appropriate emoji based on trend direction
        if direction == 'increasing':
            emoji = "📈"
        elif direction == 'decreasing':
            emoji = "📉"
        else:
            emoji = "➡️"
        
        report += f"### {col} {emoji}\n"
        report += f"- **Trend Direction**: {direction}\n"
        report += f"- **Correlation**: {correlation:.3f}\n\n"
    
    # Add action items if available
    if action_items and 'action_items' in action_items:
        report += "## Recommended Actions\n\n"
        for item in action_items['action_items']:
            priority = item.get('priority', 'medium')
            category = item.get('category', 'general')
            title = item.get('title', 'Untitled Action')
            description = item.get('description', 'No description available')
            expected_impact = item.get('expected_impact', 'Impact not specified')
            timeline = item.get('timeline', 'Timeline not specified')
            responsible = item.get('responsible', 'Not specified')
            
            # Add priority indicator
            if priority == 'high':
                priority_indicator = "🔴"
            elif priority == 'medium':
                priority_indicator = "🟡"
            else:
                priority_indicator = "🟢"
            
            report += f"### {priority_indicator} {title}\n"
            report += f"- **Category**: {category}\n"
            report += f"- **Priority**: {priority}\n"
            report += f"- **Description**: {description}\n"
            report += f"- **Expected Impact**: {expected_impact}\n"
            report += f"- **Timeline**: {timeline}\n"
            report += f"- **Responsible**: {responsible}\n\n"
    
    # Add timestamp
    report += f"\n---\n\n*Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
    
    return report