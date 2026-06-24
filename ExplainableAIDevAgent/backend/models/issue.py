from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database.database import Base

class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"))
    gitlab_issue_id = Column(Integer, unique=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    state = Column(String, index=True)
    labels = Column(String)
    
    assignee_id = Column(Integer, ForeignKey("contributors.id", ondelete="SET NULL"), nullable=True)
    
    gitlab_created_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assignee = relationship("Contributor", back_populates="issues")
    project = relationship("Project")
