from fastapi import APIRouter, HTTPException, Depends
from typing import List
import time
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from app.models import SearchRequest, SearchResponse, SearchResult
from db_manager import DatabaseManager
from elasticsearch_manager import ElasticsearchManager
from app.search_engine import get_search_engine

router = APIRouter(prefix="/api", tags=["search"])

@router.post("/search", response_model=SearchResponse)
async def search_articles(request: SearchRequest):
    try:
        start_time = time.time()
        
        search_engine = get_search_engine()
        
        if request.compare:
            search_results = search_engine.bm25_search(request.query, request.top_n)
            results = [
                SearchResult(
                    id=result['id'],
                    title=result['title'],
                    url=result['url'],
                    score=result['score'],
                    ml_score=result['score'],
                    bm25_score=result['score'],
                    views=result['views'],
                    comments_count=result['comments_count'],
                    tags=result['tags']
                )
                for result in search_results
            ]
        else:
            search_results = search_engine.smart_search(request.query, request.top_n)
            results = [
                SearchResult(
                    id=result['id'],
                    title=result['title'],
                    url=result['url'],
                    score=result['score'],
                    ml_score=result['ml_score'],
                    bm25_score=result['bm25_score'],
                    views=result['views'],
                    comments_count=result['comments_count'],
                    tags=result['tags']
                )
                for result in search_results
            ]
        
        search_time = time.time() - start_time
        
        return SearchResponse(
            query=request.query,
            results=results,
            total_results=len(results),
            search_time=search_time
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка поиска: {str(e)}")

@router.get("/stats")
async def get_database_stats():
    try:
        search_engine = get_search_engine()
        
        search_stats = search_engine.get_search_stats()
        
        db_manager = DatabaseManager()
        articles = db_manager.get_articles_for_search()
        
        total_views = sum(article.get('views', 0) for article in articles)
        total_articles = len(articles)
        avg_views = total_views / total_articles if total_articles > 0 else 0
        
        hub_counts = {}
        for article in articles:
            tags = article.get('tags', []) or []
            for tag in tags:
                hub_counts[tag] = hub_counts.get(tag, 0) + 1
        
        top_hubs = [
            {'hub': hub, 'count': count}
            for hub, count in sorted(hub_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        
        return {
            'total_articles': total_articles,
            'total_views': total_views,
            'avg_views': avg_views,
            'top_hubs': top_hubs,
            'es_index_size': search_stats.get('elasticsearch', {}).get('index_size', 0),
            'es_total_docs': search_stats.get('elasticsearch', {}).get('total_docs', 0),
            'ml_model': search_stats.get('ml_model', {})
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения статистики: {str(e)}")


@router.get("/ml-model/status")
async def get_ml_model_status():
    try:
        search_engine = get_search_engine()
        ml_stats = search_engine.ml_ranker.get_model_info()
        
        return {
            'status': 'ready' if ml_stats.get('ready', False) else 'not_ready',
            'model_loaded': ml_stats.get('model_loaded', False),
            'features_count': ml_stats.get('features_count', 0),
            'feature_columns': ml_stats.get('feature_columns', []),
            'tfidf_loaded': ml_stats.get('tfidf_loaded', False)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения статуса ML модели: {str(e)}")

@router.get("/top-articles")
async def get_top_articles(limit: int = 10):
    try:
        db_manager = DatabaseManager()
        articles = db_manager.get_top_articles(limit)
        return articles
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения топ статей: {str(e)}")

@router.get("/articles/hub/{hub}")
async def get_articles_by_hub(hub: str, limit: int = 20):
    try:
        db_manager = DatabaseManager()
        articles = db_manager.search_articles_by_title(hub, limit)
        return articles
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения статей по хабу: {str(e)}")
