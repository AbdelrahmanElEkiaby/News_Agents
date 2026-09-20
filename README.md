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

## Phase 3 Features

- OpenAI article classification for newly saved articles
- Structured output using a Pydantic model
- Stores `category` and `topics` in PostgreSQL
- Skips duplicate URLs so old articles are not classified again

## Phase 4 Features

- OpenAI article summarization for newly saved articles
- Short summaries in the article language
- Key points stored with each article
- Skips duplicate URLs so old articles are not summarized again
- Basic article content extraction using `httpx` and BeautifulSoup
- Updates missing content on duplicate articles when the same URL is fetched again

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

## Current News Sources

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
|   |   `-- preference.py
|   |-- services/
|   |   |-- __init__.py
|   |   |-- article_classification.py
|   |   |-- article_summarization.py
|   |   |-- article_storage.py
|   |   |-- news_collection.py
|   |   |-- pipeline.py
|   |   |-- scheduler.py
|   |   `-- relevance.py
|   `-- sources/
|       |-- __init__.py
|       |-- article_content.py
|       |-- hacker_news.py
|       |-- rss.py
|       `-- rss_sources.py
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
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5433/news_agents
NEWS_FETCH_INTERVAL_MINUTES=30
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
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

Expected response:

```json
{
  "fetched": 20,
  "saved": 5,
  "duplicates": 15,
  "content_updated": 10,
  "classified": 5,
  "summarized": 5
}
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
