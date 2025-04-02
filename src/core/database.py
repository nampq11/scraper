from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import JSON, Column, DateTime, String, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base  # Updated import for SQLAlchemy 2.0 compatibility
from pydantic import BaseModel, ConfigDict

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()  # This line is fine now with the updated import


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True)
    url = Column(String)
    operation = Column(String)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)
    error = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    formats = Column(JSON, nullable=True)
    page_options = Column(JSON, nullable=True)


class ScrapedContent(Base):
    __tablename__ = "scraped_content"

    job_id = Column(String, primary_key=True)
    url = Column(String)
    content = Column(JSON)
    metadata_content = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)


# Pydantic models for API interactions - using ConfigDict instead of class Config
class JobBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    url: str
    operation: str
    formats: Optional[Dict[str, Any]] = None
    page_options: Optional[Dict[str, Any]] = None


class JobCreate(JobBase):
    pass


class JobResponse(JobBase):
    id: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None


class ScrapedContentBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    url: str
    content: Dict[str, Any]
    metadata_content: Dict[str, Any]


class ScrapedContentCreate(ScrapedContentBase):
    job_id: str


class ScrapedContentResponse(ScrapedContentBase):
    job_id: str
    created_at: datetime


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


Base.metadata.create_all(bind=engine)
