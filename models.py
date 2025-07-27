from pydantic import BaseModel
from typing import List

class NewsRequest(BaseModel):
    topics: List[str]
    source_type: str               # "news" | "reddit" | "both"
    language: str = "en-US"        # Murf locale code, e.g. "en-US", "es-ES"
