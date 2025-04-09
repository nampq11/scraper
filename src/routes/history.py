from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.core.database import Job, ScrapedContent, get_db
from src.core.job_manager import JobManager

router = APIRouter()
job_manager = JobManager()


@router.get("/")
async def get_history(
    limit: int = Query(20, gt=0, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
    days: Optional[int] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Job)

    if status:
        query = query.filter(Job.status == status)

    if days:
        since = datetime.now() - timedelta(days=days)
        query = query.filter(Job.created_at >= since)

    total = query.count()
    jobs = query.order_by(Job.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "jobs": [
            {
                "id": job.id,
                "operation": job.operation,
                "status": job.status,
                "url": job.url,
                "created_at": job.created_at.isoformat(),
                "completed_at": job.completed_at.isoformat()
                if job.completed_at
                else None,
            }
            for job in jobs
        ],
    }


@router.get("/{job_id}/content")
async def get_job_content(job_id: str, db: Session = Depends(get_db)):
    content = db.query(ScrapedContent).filter(ScrapedContent.job_id == job_id).first()

    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    return {
        "url": content.url,
        "metadata": content.metadata_content,
        "content": content.content,
        "created_at": content.created_at.isoformat(),
    }
