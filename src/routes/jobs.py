from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.job_manager import JobManager

router = APIRouter()
job_manager = JobManager()


@router.get("/{job_id}")
async def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
):
    """
    Get the status and results of a job.

    Returns:
    - Job status, metadata, and results if completed
    - Error details if job failed
    - 404 if job not found
    """
    status = job_manager.get_job_status(db, job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status
