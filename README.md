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

## Article Intelligence Features

- One Jev decision request classifies each article with bounded language, category, topic, and importance values
- OpenAI is called only when a user requests a summary for one article
- Stores classification confidence and a normalized importance score in PostgreSQL
- Stores language, category, topics, summary, and key points in PostgreSQL
- Short summaries are written in the article language
- Duplicate URLs are removed before article pages or AI services are requested
- Article pages are downloaded concurrently with a bounded worker count
- User scans classify waiting articles with Jev but do not call OpenAI
- Generated summaries are stored and reused without another model call
- Concurrent duplicate requests are blocked and failures have a retry cooldown

## Phase 5 Features

- Local user profiles are stored in PostgreSQL
- Users subscribe to shared sources through the `user_sources` table
- Public feeds are fetched once and reused by every subscribed user
- Each user sees articles from their subscribed sources
- Email and password authentication uses expiring JWT bearer tokens
- Passwords are hashed with Argon2 and are never stored as plain text

## Legacy Ranking API

- `POST /feed` accepts preferences directly in the request body
- Calculates AI relevance for saved articles
- Adds deterministic freshness and topic-match scores
- Returns articles ordered by final score
- The current frontend does not call this endpoint

## Phase 7 Features

- Background scheduler for the news pipeline
- Fetch interval controlled by `NEWS_FETCH_INTERVAL_MINUTES`
- Scans all active sources and processes missing classifications
- Never generates summaries automatically

## Phase 8 Features

- React and TypeScript frontend
- Source-first workflow with a dedicated scan button
- Categories and topics are generated dynamically from saved articles
- Category and topic filtering happens locally without an AI request
- Article details display saved content and offer on-demand summary generation
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
- Source definitions come only from PostgreSQL; there is no startup source list

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
   |
User Subscriptions
```

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
|   |   |-- source.py
|   |   `-- user.py
|   |-- schemas/
|   |   |-- __init__.py
|   |   |-- article.py
|   |   |-- source.py
|   |   `-- user.py
|   |-- routers/
|   |   |-- __init__.py
|   |   |-- articles.py
|   |   |-- auth.py
|   |   |-- sources.py
|   |   `-- users.py
|   |-- services/
|   |   |-- __init__.py
|   |   |-- article_classification.py
|   |   |-- article_content.py
|   |   |-- article_context.py
|   |   |-- article_service.py
|   |   |-- article_summary_service.py
|   |   |-- article_summarization.py
|   |   |-- auth_service.py
|   |   |-- feed_discovery.py
|   |   |-- news_pipeline.py
|   |   |-- relevance.py
|   |   |-- rss_service.py
|   |   |-- scheduler.py
|   |   |-- source_service.py
|   |   `-- user_service.py
|-- .env.example
|-- docker-compose.yml
|-- frontend/
|   |-- src/
|   |   |-- AuthPage.tsx
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
JEV_API_KEY=
JEV_MODEL=jev-latest
DATABASE_URL=postgresql+psycopg://postgres:newsagent123@localhost:5433/news_agents
NEWS_FETCH_INTERVAL_MINUTES=30
JWT_SECRET_KEY=replace-with-a-random-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

Generate a local JWT signing secret with `openssl rand -hex 32` and place it in `.env`.

For production, set `CORS_ORIGINS` to the public frontend URL. Multiple frontend URLs can
be provided as a comma-separated list. Do not include a trailing slash:

```env
CORS_ORIGINS=https://your-news-agent.onrender.com
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

Except for `/`, `/auth/register`, and `/auth/login`, API requests require the JWT returned by
registration or login in an `Authorization: Bearer ...` header.

## Fetch And Save Articles

```bash
curl -X POST http://127.0.0.1:8000/articles/fetch \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

The manual endpoint scans only the signed-in user's subscribed sources. It fetches article pages
and classifies waiting articles with Jev before returning. It does not call OpenAI summarization.
When no new items are found, existing saved articles remain available in the frontend.

The scheduler separately scans all active sources based on `NEWS_FETCH_INTERVAL_MINUTES` and
processes classifications only. It never generates summaries automatically.

The pipeline now reads active rows from the `sources` table. A disabled source is skipped automatically.

Expected response:

```json
{
  "fetched": 20,
  "saved": 5,
  "duplicates": 15,
  "content_updated": 10,
  "classified": 5,
  "summarized": 0,
  "ai_processing_started": false
}
```

To queue a classification backfill without fetching feeds again, use:

```bash
curl -X POST http://127.0.0.1:8000/articles/process-missing \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## List Saved Articles

```text
http://127.0.0.1:8000/articles
```

## Read One Article

```text
http://127.0.0.1:8000/articles/1
```

## Generate One Summary

```bash
curl -X POST http://127.0.0.1:8000/articles/1/summary \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

The endpoint returns an existing summary without an OpenAI request. For an unsummarized article,
the database reserves the work before calling OpenAI, preventing duplicate calls across clicks,
tabs, or users. A user can start at most five new summaries per minute. Failed requests have a
60-second retry cooldown and abandoned processing locks can be retried after five minutes.

Saved articles now include classification fields:

```json
{
  "id": 1,
  "title": "Example news title",
  "source": "BBC News",
  "language": "en",
  "content": "Extracted article text...",
  "category": "world",
  "topics": ["middle_east", "geopolitics"],
  "importance": "high",
  "importance_score": 0.6667,
  "classification_confidence": 0.91,
  "summary": "A short summary of the article.",
  "key_points": ["First key point", "Second key point"]
}
```

## Dynamic Feed Filtering

The frontend loads saved articles with `GET /articles`. It derives the available category and
topic cards from those rows. Selecting a card filters the loaded articles in the browser and does
not call OpenAI or the legacy `/feed` ranking endpoint.

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

## Authentication API

Register an account:

```bash
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Ahmed","email":"ahmed@example.com","password":"strong-password"}'
```

Login uses OAuth2 form fields and returns a JWT:

```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=ahmed@example.com&password=strong-password"
```

Send the returned token to protected endpoints:

```text
Authorization: Bearer YOUR_ACCESS_TOKEN
```

## User Subscriptions API

Subscriptions always belong to the authenticated user:

```text
GET /users/me/sources
POST /users/me/sources/{source_id}
DELETE /users/me/sources/{source_id}
```

`POST /feed` automatically uses the authenticated user's subscriptions. A user ID is never
accepted from the browser for feed or subscription ownership.
