import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import create_database_tables
from app.routers import articles, auth, sources, users
from app.services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_database_tables()
    app.state.scheduler = start_scheduler()

    try:
        yield
    finally:
        stop_scheduler()


app = FastAPI(title="News Agent API", lifespan=lifespan)
app.state.settings = settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(articles.router)
app.include_router(auth.router)
app.include_router(sources.router)
app.include_router(users.router)


@app.get("/")
async def read_root():
    return {"message": "News Agent API is running"}
