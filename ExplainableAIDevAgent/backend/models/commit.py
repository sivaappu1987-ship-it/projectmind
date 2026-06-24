from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database.database import Base

class Commit(Base):
    __tablename__ = "commits"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"))
    hash = Column(String, unique=True, index=True, nullable=False)
    message = Column(Text)
    commit_date = Column(DateTime)
    
    contributor_id = Column(Integer, ForeignKey("contributors.id", ondelete="CASCADE"))
    
    created_at = Column(DateTime, default=datetime.utcnow)

    contributor = relationship("Contributor", back_populates="commits")
    project = relationship("Project")
