import sys
import os
import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)

def test_scape_endpoint():
    """Test basic scraping functionality."""
    response = client.post(
        "/api/scrape/async",
        json={
            "url": "https://quotes.toscrape.com/tag/humor/",
            "formats": ["markdown"],
            "page_options": {
                "extract_main_content": True,
                "clean_markdown": True
            }
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data['status'] == "pending"

def test_job_status():
    """Test job status retrieval."""
    response = client.post(
        "/api/scrape/async",
        json={
            "url": "https://quotes.toscrape.com/tag/humor/",
            "formats": ["markdown"],
        }
    )
    job_id = response.json()["job_id"]

    response = client.get(f"/api/jobs/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "operation" in data
    assert data["operation"] == "scrape"

def test_history():
    """Test history endpoint with operation feild."""
    response = client.get("/api/history")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "jobs" in data
    if data["jobs"]:
        job = data["jobs"][0]
        assert "operation" in job
        assert "status" in job
        assert "url" in job

