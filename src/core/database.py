from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


Base.metadata.create_all(bind=engine)
