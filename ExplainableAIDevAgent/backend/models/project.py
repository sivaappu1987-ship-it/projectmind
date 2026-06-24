from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from backend.database.database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    gitlab_id = Column(Integer, unique=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    visibility = Column(String)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
