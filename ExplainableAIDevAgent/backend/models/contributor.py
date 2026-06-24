from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database.database import Base

class Contributor(Base):
    __tablename__ = "contributors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    total_commits = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    commits = relationship("Commit", back_populates="contributor", cascade="all, delete-orphan")
    merge_requests = relationship("MergeRequest", back_populates="author", cascade="all, delete-orphan")
    issues = relationship("Issue", back_populates="assignee", cascade="all, delete-orphan")
