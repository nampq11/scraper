# Scraper API documentation

## Small Firecrawl alternative

## Overview
Scraper is an asynchronous web scraping and crawling service that provides:
- Clean, LLM-ready markdown output
- Configurable content extraction
- Web crawling with depth and path filtering
- URL mapping and discovery
- Job management and history tracking

## API endpoints

### Scraping Endpoints

#### 1. Start a Scraping Job
**Endpoint:** `POST /api/scrape/async`

**Example Request:**
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/api/scrape/async' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "url": "https://example.com/",
  "formats": [
    "markdown"
  ],
  "page_options": {
    "extract_main_content": true,
    "include_links": false,
    "structured_json": false,
    "use_browser": false,
    "max_retries": 3
  }
}'
```

### Crawling Endpoints

#### 1. Start a Crawl Job
**Endpoint:** `POST /api/crawl/async`
**Example Request:**
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/api/crawl/async' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "url": "https://example.com/",
  "options": {
    "formats": [
      "markdown"
    ],
    "exclude_paths": [],
    "include_only_paths": [],
    "allow_backwards": false,
    "include_subdomains": false,
    "ignore_subdomains": false,
    "page_options": {
      "exclude_tags": [
        "script",
        "style",
        "noscript",
        ".ad",
        "#footer"
      ],
      "extract_main_content": true,
      "include_links": true,
      "structured_json": true,
      "wait_for": 1000
    }
  }
}'
```

### URL Mapping Endpoints

#### 1. Map website URLs
**Endpoint:** `POST /api/map`

**Example Request:**
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/api/map/3f6af517-ee3d-443f-9788-f592ed78f1dd' \
  -H 'accept: application/json'
```

### Job Management Endpoints

#### 1. Check Job Status
**Endpoint:** `GET /api/job/{job_id}`

**Example response:**
```json
{
  "id": "3f6af517-ee3d-443f-9788-f592ed78f1dd",
  "operation": "crawl",
  "status": "completed",
  "url": "https://example.com/",
  "created_at": "2025-04-02T22:49:33.181754",
  "completed_at": "2025-04-02T22:49:34.144030",
  "error": null,
  "result": {
    "metadata_content": {
      "total_pages": 1,
      "depth_reached": 0,
      "start_time": "2025-04-02T22:49:33.192137",
      "end_time": "2025-04-02T22:49:34.140467",
      "options": {
        "formats": [
          "markdown"
        ],
        "exclude_paths": [],
        "include_only_paths": [],
        "allow_backwards": false,
        "include_subdomains": false,
        "ignore_subdomains": false,
        "page_options": {
          "extract_main_content": true,
          "include_links": true,
          "structured_json": true,
          "exclude_tags": [
            "script",
            "style",
            "noscript",
            ".ad",
            "#footer"
          ],
          "wait_for": 1000
        }
      }
    },
    "content": {
        "markdown": "..."
    }
  }
}
```

#### 2. View Job History
**Endpoint:** `GET /api/history`

**Parameters:**
- `limit`: Number of results (default: 20)
- `offset`: Pagination offset (default: 0)
- `status`: Filter by status
- `days`: Filter by N days

## Configuration Options

### Page Options
| Option               | Type    | Default | Description                                      |
|----------------------|---------|---------|--------------------------------------------------|
| extract_main_content | boolean | true    | Extract main content using readability algorithm |
| clean_markdown       | boolean | true    | Apply additional markdown clearning rules        |
| include_links        | boolean | false   | Include all links in the results                 |
| structured_json      | boolean | false   | Structure content as JSON where possible         |
| use_browser          | boolean | false   | use headless browser for javascript rendering    |
| wait_for             | integer | null    | Milliseconds to wait after page load             |
| exclude_tags         | array   | []      | HTML tags/selectors to exclude                   |
| max_retries          | integer | 3       | Maximum retry attempts for failed requests       |

### Markdown Cleaning 
when `clean_markdown: true` is set, the following rules are applied:
- Remove redundant whitespace
- Normalize header levels
- Clean list formatting
- Remove HTML comments
- Normalize line endings
- Add proper spacing around headers and lists
- Remove duplicate blank lines
