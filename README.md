# Personalized News Agent

A small FastAPI project for building a bilingual Arabic and English personalized news agent.

This project is being built one phase at a time.

## Phase 0 Features

- FastAPI application
- `GET /` health check endpoint
- Environment variable loading from `.env`
- Config values for OpenAI and the database

## Phase 1 Features

- Fetch recent articles from three sources
- Normalize API and RSS results into one `Article` model
- Basic error handling for unavailable sources and bad entries

## Phase 2 Features

- PostgreSQL database storage
- `articles` table
- Unique URL duplicate detection
- `POST /articles/fetch` to fetch and save new articles
- `GET /articles` to list saved articles
- `GET /articles/{id}` to read one saved article

## Phase 3 And 4 Features

- One structured OpenAI request classifies and summarizes each article
- Stores language, category, topics, summary, and key points in PostgreSQL
- Short summaries are written in the article language
- Duplicate URLs are removed before article pages or OpenAI are requested
- Article pages are downloaded concurrently with a bounded worker count
- Manual fetches queue AI processing in the background
- Existing rows with missing summaries are included in the next background pass

## Phase 5 Features

- Preferences are represented as a simple request model
- Preferences are not stored in PostgreSQL yet
- Future relevance endpoints can receive topics and languages directly in the API request
- No authentication yet

## Phase 6 Features

- `POST /feed` accepts preferences directly in the request body
- Calculates AI relevance for saved articles
- Adds deterministic freshness and topic-match scores
- Returns articles ordered by final score
- Limits each request to a small number of articles to control OpenAI cost

## Phase 7 Features

- Background scheduler for the news pipeline
- Fetch interval controlled by `NEWS_FETCH_INTERVAL_MINUTES`
- Uses the same pipeline as `POST /articles/fetch`
- Logs fetch, save, duplicate, classification, and summarization counts

## Phase 8 Features

- React and TypeScript frontend
- Feed ranking screen
- Preference controls for topics, languages, and article count
- Article details panel with summary, ranking scores, topics, and original link
- Uses normal React hooks and `fetch`

## Dynamic Sources

- News sources are stored in the `sources` table
- The scheduler loads active sources from PostgreSQL
- RSS sources use one generic RSS fetcher
- Adding a normal RSS source does not require changing backend code
- `DELETE /sources/{id}` safely disables a source by setting `is_active = false`
- The backend can discover RSS or Atom feeds from a website URL
- The frontend has a Sources screen for adding, enabling, disabling, and deleting sources
- A direct RSS or Atom URL can be supplied when a website blocks automatic discovery
- Direct feed URLs are validated before they are stored
- Discovery collects and ranks every valid feed it finds instead of accepting the first URL
- The frontend recommends one feed and shows a selector when a website has multiple feeds
- Fetch failures are recorded on the source without stopping other sources

```text
Website
   |
RSS Discovery
   |
Source Database
   |
Scheduler
   |
Generic RSS Fetcher
   |
Articles
   |
AI Pipeline
```

## Seeded News Sources

- Al Jazeera Arabic RSS
- BBC News RSS

## Project Structure

```text
News_Agents/
|-- app/
|   |-- __init__.py
|   |-- config.py
|   |-- database.py
|   |-- main.py
|   |-- models/
|   |   |-- __init__.py
|   |   |-- article.py
|   |   |-- article_db.py
|   |   |-- feed.py
|   |   |-- preference.py
|   |   |-- source.py
|   |   `-- source_db.py
|   |-- services/
|   |   |-- __init__.py
|   |   |-- article_analysis.py
|   |   |-- article_storage.py
|   |   |-- news_collection.py
|   |   |-- pipeline.py
|   |   |-- scheduler.py
|   |   |-- relevance.py
|   |   `-- source_storage.py
|   `-- sources/
|       |-- __init__.py
|       |-- article_content.py
|       |-- feed_discovery.py
|       |-- rss.py
|       `-- source_fetcher.py
|-- .env.example
|-- docker-compose.yml
|-- frontend/
|   |-- src/
|   |   |-- api.ts
|   |   |-- main.tsx
|   |   |-- styles.css
|   |   `-- vite-env.d.ts
|   |-- index.html
|   |-- package.json
|   |-- tsconfig.json
|   `-- vite.config.ts
|-- requirements.txt
`-- README.md
```

## Environment Variables

Create a `.env` file using `.env.example` as a guide:

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5-nano
DATABASE_URL=postgresql+psycopg://postgres:newsagent123@localhost:5433/news_agents
NEWS_FETCH_INTERVAL_MINUTES=30
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Start PostgreSQL

```bash
docker compose up -d postgres
```

The included Docker Compose file exposes PostgreSQL on port `5433` to avoid conflicts with a local PostgreSQL install on port `5432`.

## Run The API

```bash
uvicorn app.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000
```

Expected response:

```json
{
  "message": "News Agent API is running"
}
```

## Fetch And Save Articles

```bash
curl -X POST http://127.0.0.1:8000/articles/fetch
```

The same pipeline also runs automatically in the background based on `NEWS_FETCH_INTERVAL_MINUTES`.
For a manual request, feed ingestion and article-page downloads finish first, then AI analysis is
queued in the background so the HTTP request does not wait for every model response.

The pipeline now reads active rows from the `sources` table. A disabled source is skipped automatically.

Expected response:

```json
{
  "fetched": 20,
  "saved": 5,
  "duplicates": 15,
  "content_updated": 10,
  "classified": 0,
  "summarized": 0,
  "ai_processing_started": true
}
```

The zero AI counts in this response mean the work was queued, not skipped. To queue a backfill
without fetching feeds again, use:

```bash
curl -X POST http://127.0.0.1:8000/articles/process-missing
```

## List Saved Articles

```text
http://127.0.0.1:8000/articles
```

## Read One Article

```text
http://127.0.0.1:8000/articles/1
```

Saved articles now include classification fields:

```json
{
  "id": 1,
  "title": "Example news title",
  "source": "BBC News",
  "language": "en",
  "content": "Extracted article text...",
  "category": "world",
  "topics": ["middle east", "diplomacy"],
  "summary": "A short summary of the article.",
  "key_points": ["First key point", "Second key point"]
}
```

## Preferences Shape

Preferences are not saved yet. Later relevance endpoints can accept this shape directly:

```json
{
  "topics": ["artificial intelligence", "technology", "middle east"],
  "languages": ["ar", "en"]
}
```

## Personalized Feed

```bash
curl -X POST http://127.0.0.1:8000/feed \
  -H "Content-Type: application/json" \
  -d "{\"topics\": [\"ai\", \"technology\", \"middle east\"], \"languages\": [\"ar\", \"en\"], \"max_articles\": 10}"
```

Expected response:

```json
[
  {
    "id": 1,
    "title": "Example article",
    "summary": "Short summary...",
    "category": "ai",
    "topics": ["artificial intelligence"],
    "score": 0.91,
    "ai_relevance": 0.9,
    "freshness_score": 1.0,
    "topic_match_score": 0.8,
    "reason": "The article matches the reader's AI interests."
  }
]
```

## Run The Frontend

Start the backend first:

```bash
uvicorn app.main:app --reload
```

Then start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

The frontend calls the backend at:

```text
http://127.0.0.1:8000
```

## Source Management API

List sources:

```text
GET /sources
```

Read one source:

```text
GET /sources/1
```

Create a source:

```bash
curl -X POST http://127.0.0.1:8000/sources \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"BBC News\", \"website_url\": \"https://www.bbc.com\", \"feed_url\": \"https://feeds.bbci.co.uk/news/rss.xml\", \"language\": \"en\", \"source_type\": \"rss\"}"
```

The backend validates direct RSS and Atom URLs before saving them. This is useful when a
publisher blocks homepage discovery or hosts its feed on another domain.

Discover a feed:

```bash
curl -X POST http://127.0.0.1:8000/sources/discover \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"https://techcrunch.com\"}"
```

Discovery checks direct feeds, RSS/Atom metadata, HTTP link metadata, RSS links and directory
pages, and common feed paths. Every candidate is parsed and scored using its discovery method,
title, item count, publication recency, and hostname. A successful response includes the ranked
feeds and the recommended feed:

```json
{
  "website_url": "https://example.com",
  "feed_url": "https://example.com/feed.xml",
  "feed_found": true,
  "message": "Found 2 RSS or Atom feed(s).",
  "recommended_feed": "https://example.com/feed.xml",
  "feeds": [
    {
      "title": "Latest News",
      "feed_url": "https://example.com/feed.xml",
      "feed_type": "rss",
      "discovery_method": "html_alternate",
      "item_count": 20,
      "latest_published_at": "2026-10-05T10:00:00Z",
      "score": 135
    }
  ]
}
```

Discovery rejects local and private IP URLs, limits redirects and response sizes, and uses request
timeouts. This prevents the public discovery endpoint from reading local services accidentally.

Add a website source with automatic RSS discovery:

```bash
curl -X POST http://127.0.0.1:8000/sources/from-website \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"https://techcrunch.com\", \"language\": \"en\"}"
```

Update a source:

```text
PATCH /sources/1
```

Disable a source:

```text
DELETE /sources/1
```

`DELETE` is a soft delete: it disables future fetching while keeping existing articles.
