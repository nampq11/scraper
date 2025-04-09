from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from .database import Job, ScrapedContent


class JobManager:
    def __init__(self):
        pass

    def _serialize_dict(self, data: Any) -> Any:
        """Convert any data structure to JSON-serializable format."""
        if hasattr(data, "dict"):
            return self._serialize_dict(data.dict(exclude_unset=True))
        elif isinstance(data, dict):
            return {key: self._serialize_dict(value) for key, value in data.items()}
        elif isinstance(data, (list, tuple)):
            return [self._serialize_dict(item) for item in data]
        elif isinstance(data, (str, int, float, bool, type(None))):
            return data
        else:
            return str(data)

    def create_job(
        self,
        db: Session,
        url: str,
        operation: str = "scrape",
        formats: list = None,
        page_options: dict = None,
    ) -> str:
        job_id = str(uuid4())

        if formats is not None:
            formats = self._serialize_dict(formats)
        if page_options is not None:
            page_options = self._serialize_dict(page_options)

        job = Job(
            id=job_id,
            url=url,
            operation=operation,
            status="pending",
            created_at=datetime.now(),
            formats=formats,
            page_options=page_options,
        )
        db.add(job)
        db.commit()
        return job_id

    def update_job(
        self,
        db: Session,
        job_id: str,
        status: str,
        result: Optional[Any] = None,
        error: Optional[str] = None,
    ):
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                return

            job.status = status
            if status in ["completed", "failed"]:
                job.completed_at = datetime.now()

            if error:
                job.error = error
                job.result = None

            if result and status == "completed":
                if isinstance(result, dict):
                    result = self._serialize_dict(result)

                existing_content = (
                    db.query(ScrapedContent)
                    .filter(ScrapedContent.job_id == job_id)
                    .first()
                )
                if existing_content:
                    db.delete(existing_content)

                scraped_content = ScrapedContent(
                    job_id=job_id,
                    url=job.url,
                    metadata_content=result.get("metadata_content", {}),
                    content=result.get("content", {}),
                )
                db.add(scraped_content)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error updating job {job_id}: {str(e)}")
            raise

    def get_job_status(self, db: Session, job_id: str) -> Optional[Dict[str, Any]]:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None

        result = {
            "id": job.id,
            "operation": job.operation,
            "status": job.status,
            "url": job.url,
            "created_at": job.created_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error": job.error,
        }

        if job.status == "completed":
            content = (
                db.query(ScrapedContent).filter(ScrapedContent.job_id == job_id).first()
            )
            if content:
                result["result"] = {
                    "metadata_content": content.metadata_content,
                    "content": content.content,
                }
        return result
