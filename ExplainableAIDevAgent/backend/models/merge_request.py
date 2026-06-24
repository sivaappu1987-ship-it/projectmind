from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database.database import Base

class MergeRequest(Base):
    __tablename__ = "merge_requests"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"))
    gitlab_mr_id = Column(Integer, unique=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    state = Column(String, index=True)
    
    author_id = Column(Integer, ForeignKey("contributors.id", ondelete="CASCADE"))
    
    gitlab_created_at = Column(DateTime)
    gitlab_updated_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    author = relationship("Contributor", back_populates="merge_requests")
    project = relationship("Project")
