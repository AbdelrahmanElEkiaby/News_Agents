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
- `GET /articles/fetch` endpoint
- Basic error handling for unavailable sources and bad entries

## Current News Sources

- Hacker News API
- Al Jazeera Arabic RSS
- BBC News RSS

## Project Structure

```text
News_Agents/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── article.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── news_collection.py
│   ├── sources/
│   │   ├── __init__.py
│   │   ├── hacker_news.py
│   │   ├── rss.py
│   │   └── rss_sources.py
│   └── main.py
├── .env.example
├── requirements.txt
└── README.md
```

## Environment Variables

Create a `.env` file using `.env.example` as a guide:

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5-nano
DATABASE_URL=
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

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

## Fetch Articles

```text
http://127.0.0.1:8000/articles/fetch
```

Expected response:

```json
[
  {
    "title": "Example news title",
    "url": "https://example.com/article",
    "source": "BBC News",
    "language": "en",
    "description": "Short description",
    "content": null,
    "published_at": "2026-09-19T18:00:00Z"
  }
]
```
