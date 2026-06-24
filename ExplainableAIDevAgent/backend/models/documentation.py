from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from datetime import datetime
from backend.database.database import Base

class Documentation(Base):
    __tablename__ = "documentation"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(Text)
    file_id = Column(Integer, ForeignKey("files.id", ondelete="SET NULL"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
