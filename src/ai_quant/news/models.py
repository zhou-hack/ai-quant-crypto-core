from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, HttpUrl


class NewsEvent(BaseModel):
    title: str
    source: str
    url: HttpUrl
    published_at: datetime
    summary: str
    impact: Literal["positive", "negative", "neutral", "uncertain"] = "uncertain"
    confidence: float = Field(ge=0, le=1)
