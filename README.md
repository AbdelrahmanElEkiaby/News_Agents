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

## Current News Sources

- Hacker News API
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
|   |   `-- article_db.py
|   |-- services/
|   |   |-- __init__.py
|   |   |-- article_classification.py
|   |   |-- article_storage.py
|   |   `-- news_collection.py
|   `-- sources/
|       |-- __init__.py
|       |-- hacker_news.py
|       |-- rss.py
|       `-- rss_sources.py
|-- .env.example
|-- docker-compose.yml
|-- requirements.txt
`-- README.md
```

## Environment Variables

Create a `.env` file using `.env.example` as a guide:

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5-nano
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5433/news_agents
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

Expected response:

```json
{
  "fetched": 30,
  "saved": 17,
  "duplicates": 13,
  "classified": 17
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
  "category": "world",
  "topics": ["middle east", "diplomacy"]
}
```
