# models/database.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import engine

Base = declarative_base()

class Report(Base):
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    file_type = Column(String)
    file_path = Column(String)
    data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    summaries = relationship("Summary", back_populates="report")

class Summary(Base):
    __tablename__ = "summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"))
    summary_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    report = relationship("Report", back_populates="summaries")

def create_tables():
    Base.metadata.create_all(bind=engine)