from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.job_manager import JobManager
from src.core.crawler import Crawler

router = APIRouter()
job_manager = JobManager()

class PageOptions(BaseModel):
    extract_main_content: bool = True
    include_links: bool = True
    structured_json: bool = True
    exclude_tags: List[str] = ['script', 'style', 'noscript', '.ad', '#footer']
    wait_for: int = 1000

class CrawlOptions(BaseModel):
    max_depth: Optional[int] = None
    max_pages: Optional[int] = None
    formats: List[str] = ["markdown"]
    exclude_paths: List[str] = []
    include_only_paths: List[str] = []
    allow_backwards: bool = False
    include_subdomains: bool = False
    ignore_subdomains: bool = False
    page_options: PageOptions = PageOptions()

    class Config:
        validate_assigment = True

class CrawlRequest(BaseModel):
    url: HttpUrl
    options: CrawlOptions = CrawlOptions()

async def background_crawl(job_id: str, url: str, options: dict):
    db = next(get_db())
    try:
        async with Crawler() as crawler:
            result = await crawler.crawl(url=url, options=options)
            
            normalize_result = {
                'metadata_content': {
                    'total_pages': result['metadata']['total_pages'],
                    'depth_reached': result['metadata']['depth_reached'],
                    'start_time': result['metadata']['start_time'],
                    'end_time': result['metadata']['end_time'],
                    'options': result['metadata']['options'],
                },
                'content': {
                    'pages': result['pages'],
                }
            }

            job_manager.update_job(db,job_id, 'completed', result=normalize_result)
    except Exception as e:
        error_msg = f"Crawling failed: {str(e)}"
        print(error_msg)
        job_manager.update_job(db, job_id, 'failed', error=error_msg)

@router.post("/async")
async def start_crawl(
    request: CrawlRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Start an asynchronous crawl job.

    The crawler will:
    - Follow links within the same domain.
    - Extract content in specified formats
    - Apply page processing options.
    - Respect path inclusion/exclusion patterns
    """
    job_id = job_manager.create_job(
        db,
        url=str(request.url),
        operation="crawl",
        formats=request.options.formats,
        page_options=request.options.page_options.model_dump(exclude_unset=True)
    )

    background_tasks.add_task(
        background_crawl,
        job_id=job_id,
        url=str(request.url),
        options=request.options.model_dump(exclude_unset=True)
    )

    return {
        'job_id': job_id,
        'status': 'pending',
        'url': str(request.url)
    }