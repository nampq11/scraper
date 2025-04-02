from fastapi import APIRouter, BackgroundTasks, Query, Depends
from pydantic import BaseModel, HttpUrl
from uuid import uuid4
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from src.core.job_manager import JobManager
from src.core.database import get_db
from src.core.crawler import Crawler
from src.core.scraper import Scraper

router = APIRouter()
job_manager = JobManager()


class PageOptions(BaseModel):
    extract_main_content: bool = True
    include_links: bool = False
    structured_json: bool = False
    use_browser: bool = False
    wait_for: Optional[int] = None
    actions: Optional[List[Dict[str, Any]]] = None
    max_retries: Optional[int] = 3
    proxy: Optional[str] = None


class ScrapeRequest(BaseModel):
    url: HttpUrl
    formats: Optional[List[str]] = ["markdown"]
    page_options: Optional[PageOptions] = PageOptions()


class BatchScrapeRequest(BaseModel):
    urls: List[HttpUrl]
    formats: Optional[List[str]] = ["markdown"]
    page_options: Optional[PageOptions] = PageOptions()


async def background_scrape(job_id: str, url: str, formats: List[str], page_options: Dict):
    db = next(get_db())
    try:
        async with Scraper() as scraper:
            result = await scraper.scrape(url=url, formats=formats, page_options=page_options)

            if result is None:
                result = {
                    "error": "Scraping returned no results",
                    "metadata": {},
                    "content": {},
                }

            if not isinstance(result, dict):
                result = {
                    "error": "Invalid result format",
                    "metadata": {},
                    "content": str(result),
                }

            normalized_result = {
                "metadata": result.get("metadata", {}),
                "content": {format_type: content for format_type, content in result.get("content", {}).items()},
            }

            if result.get("error"):
                normalized_result["metadata_content"]["error"] = result["error"]

            job_manager.update_job(db, job_id, "completed", result=normalized_result)
    except Exception as e:
        error_msg = f"Scraping failed: {str(e)}"
        print(error_msg)
        job_manager.update_job(db, job_id, "failed", error=error_msg)
    finally:
        db.close()


@router.post("/async")
async def start_scrape(request: ScrapeRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Start an asynchronous scraping job.

    The scraper will:
    - Extract content in specified formats (default: markdown)
    - Apply page processing options
    - Return structured content with metadata
    """
    job_id = job_manager.create_job(
        db,
        url=str(request.url),
        operation="scrape",
        formats=request.formats,
        page_options=request.page_options.model_dump(exclude_none=True),
    )

    background_tasks.add_task(
        background_scrape,
        job_id,
        str(request.url),
        request.formats,
        request.page_options.model_dump(exclude_unset=True),
    )
    return {
        "job_id": job_id,
        "status": "pending",
        "url": str(request.url),
    }


@router.post("/batch")
async def start_batch_scrape(
    request: BatchScrapeRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """
    Start multiple scraping jobs in batch.

    Return a list of job IDs that can be used to check status
    and retrieve results.
    """
    job_ids = []
    for url in request.urls:
        job_id = job_manager.create_job(
            db,
            url=str(url),
            operation="scrape_batch",
            formats=request.formats,
            page_options=request.page_options.model_dump(exclude_none=True),
        )

        job_ids.append(job_id)
        background_tasks.add_task(
            background_scrape, job_id, url, request.formats, request.page_options.model_dump(exclude_unset=True)
        )

    return {"job_ids": job_ids, "total_jobs": len(job_ids), "status": "pending"}
