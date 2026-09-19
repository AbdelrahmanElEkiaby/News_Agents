from pydantic import BaseModel


class Preferences(BaseModel):
    topics: list[str]
    languages: list[str]
