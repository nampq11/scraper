from fastapi import APIRouter, FastAPI

from src.routes import crawl, history, jobs, map, scrape

app = FastAPI(
    title="Scraper API",
    description="""
    Asynchronous web scraping and crawling API with job management.

    Features:
    - Single page scraping with customizable formats
    - URL mapping and discovery
    - Job history and status tracking
    - Cleaning markdown output for LLM processing
    """,
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

api_router = APIRouter(prefix="/api")

api_router.include_router(crawl.router, prefix="/crawl", tags=["crawling"])
api_router.include_router(scrape.router, prefix="/scrape", tags=["scraping"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(history.router, prefix="/history", tags=["history"])
api_router.include_router(map.router, prefix="/map", tags=["mapping"])

app.include_router(api_router)


@app.get("/")
async def root():
    return {"status": "running", "docs": "/api/docs", "redoc": "/api/redoc"}
