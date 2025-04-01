from fastapi import FastAPI, APIRouter

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

app.include_router(api_router)

@app.get("/")
async def root():
    return {
        "status": "running",
        "docs": "/api/docs",
        "redoc": "/api/redoc"
    }
