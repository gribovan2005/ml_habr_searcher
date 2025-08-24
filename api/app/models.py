from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class SearchRequest(BaseModel):
    query: str
    top_n: int = 10
    compare: bool = False

class SearchResult(BaseModel):
    id: int
    title: str
    url: str
    score: float
    ml_score: float
    bm25_score: float
    views: int
    comments_count: int
    tags: List[str]

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total_results: int
    search_time: float

class DatabaseStats(BaseModel):
    total_articles: int
    total_views: int
    avg_views: float
    top_hubs: List[dict]

class SearchHistory(BaseModel):
    query: str
    timestamp: datetime
    results_count: int

class Article(BaseModel):
    id: int
    url: str
    title: str
    text_content: str
    tags: List[str]
    views: int
    score: int
    comments_count: int
    scraped_at: datetime
