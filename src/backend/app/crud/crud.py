# crud/crud.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from models.database import Report, Summary
from models.schemas import ReportCreate, SummaryCreate

def create_report(db: Session, report: ReportCreate) -> Report:
    db_report = Report(
        filename=report.filename,
        file_type=report.file_type,
        file_path=report.file_path,
        data=report.data
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report

def get_report_by_file_id(db: Session, file_id: str):
    report = db.query(Report).filter(
        func.json_extract(Report.data, '$.file_id') == file_id
    ).first()
    return report

def get_report(db: Session, report_id: int):
    report = db.query(Report).filter(Report.id == report_id).first()
    return report

def create_summary(db: Session, summary: SummaryCreate) -> Summary:
    db_summary = Summary(
        report_id=summary.report_id,
        summary_text=summary.summary_text
    )
    db.add(db_summary)
    db.commit()
    db.refresh(db_summary)
    return db_summary

def get_summary_by_report_id(db: Session, report_id: int):
    summary = db.query(Summary).filter(Summary.report_id == report_id).first()
    return summary