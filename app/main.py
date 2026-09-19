from fastapi import FastAPI

from app.config import settings

app = FastAPI(title="News Agent API")
app.state.settings = settings


@app.get("/")
async def read_root():
    return {"message": "News Agent API is running"}
