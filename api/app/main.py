from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
import os
import uvicorn

from routers import search

app = FastAPI(
    title="Habr Searcher",
    description="API для двухэтапной системы поиска статей с Habr.com",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:80", "http://127.0.0.1:80"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router)

instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)

@app.get("/")
async def root():
    return {
        "message": "Habr Searcher",
        "version": "1.0.0",
        "description": "двухэтапная система поиска статей с Habr.com",
        "endpoints": {
            "search": "POST /api/search - поиск статей",
            "stats": "GET /api/stats - статистика базы данных",
            "top_articles": "GET /api/top-articles - Топ статей",
            "articles_by_hub": "GET /api/articles/hub/{hub} - Статьи по хабу"
        },
        "docs": {
            "swagger": "/docs",
            "redoc": "/redoc"
        },
        "frontend": "http://localhost:3000"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "habr-search-api"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
