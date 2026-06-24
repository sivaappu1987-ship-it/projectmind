from sqlalchemy import Column, Integer, String, JSON, DateTime
from sqlalchemy.sql import func
from backend.database.database import Base

class AnalysisLog(Base):
    """
    Phase 8: Audit Logging for all decisions made by the Explainable AI.
    """
    __tablename__ = "analysis_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_type = Column(String, index=True) # risk, onboarding, drift
    entity_id = Column(String)
    result = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
