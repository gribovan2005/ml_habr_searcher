import os
import sys
import time
import logging
from typing import List, Dict, Any

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from elasticsearch_manager import ElasticsearchManager
from redis_manager import RedisManager
from db_manager import DatabaseManager
from app.ml_ranker import MLRanker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_search_engine = None

class SearchEngine:
    
    def __init__(self):

        self.db_manager = DatabaseManager()
        self.es_manager = ElasticsearchManager()
        self.redis_manager = RedisManager()
        
        self.ml_ranker = MLRanker()
        
        logger.info(f"SearchEngine инициализирован. ML модель готова: {self.ml_ranker.is_ready()}")
        if self.ml_ranker.is_ready():
            logger.info(f"Модель содержит {len(self.ml_ranker.feature_columns)} признаков")
    
    def bm25_search(self, query: str, top_n: int = 10) -> List[Dict[str, Any]]:

        start_time = time.time()
        
        cached_results = self.redis_manager.get_cached_search_results(f"bm25_{query}", top_n)
        if cached_results:
            logger.info(f"BM25 поиск '{query}': {len(cached_results)} результатов из кэша")
            return cached_results
        
        candidates = self.es_manager.search_articles(query, top_n)
        
        formatted_results = []
        for candidate in candidates:
            try:
                doc_id = candidate['doc_id']
                
                article_data = self.redis_manager.get_cached_article_metadata(doc_id)
                if not article_data:
                    article_data = self.db_manager.get_article_by_habr_id(str(doc_id))
                    if article_data:
                        self.redis_manager.cache_article_metadata(doc_id, article_data)
                
                if article_data:
                    result = {
                        'id': doc_id,
                        'title': article_data['title'],
                        'url': article_data['url'],
                        'score': candidate['bm25_score'],
                        'bm25_score': candidate['bm25_score'],
                        'ml_score': candidate['bm25_score'],  
                        'views': article_data.get('views', 0),
                        'comments_count': article_data.get('comments_count', 0),
                        'tags': article_data.get('tags', []),
                        'highlights': candidate.get('highlights', {})
                    }
                    formatted_results.append(result)
            
            except Exception as e:
                logger.warning(f"Ошибка обработки кандидата {candidate.get('doc_id', 'unknown')}: {e}")
                continue
        
        if formatted_results:
            self.redis_manager.cache_search_results(f"bm25_{query}", top_n, formatted_results)
        
        search_time = time.time() - start_time
        logger.info(f"BM25 поиск '{query}': {len(formatted_results)} результатов за {search_time:.3f}с")
        
        return formatted_results
    
    def smart_search(self, query: str, top_n: int = 10) -> List[Dict[str, Any]]:

        start_time = time.time()
        
        if not self.ml_ranker.is_ready():
            logger.warning("ML модель не готова, используем BM25 поиск")
            return self.bm25_search(query, top_n)
        
        cached_results = self.redis_manager.get_cached_search_results(f"ml_{query}", top_n)
        if cached_results:
            logger.info(f"ML поиск '{query}': {len(cached_results)} результатов из кэша")
            return cached_results
        

        candidates = self.es_manager.search_articles(query, 100)
        
        if not candidates:
            logger.info(f"ML поиск '{query}': кандидаты не найдены")
            return []
        
        logger.info(f"ML поиск '{query}': получено {len(candidates)} кандидатов от BM25")
        
        enriched_candidates = []
        for candidate in candidates:
            try:
                doc_id = candidate['doc_id']
                
                article_data = self.redis_manager.get_cached_article_metadata(doc_id)
                if not article_data:
                    article_data = self.db_manager.get_article_by_habr_id(str(doc_id))
                    if article_data:
                        self.redis_manager.cache_article_metadata(doc_id, article_data)
                
                if article_data:
                    enriched_candidate = {
                        'id': doc_id,
                        'title': article_data['title'],
                        'url': article_data['url'],
                        'text_content': article_data.get('text_content', ''),
                        'tags': article_data.get('tags', []),
                        'views': article_data.get('views', 0),
                        'score': article_data.get('score', 0),
                        'comments_count': article_data.get('comments_count', 0),
                        'bm25_score': candidate['bm25_score'],
                        'highlights': candidate.get('highlights', {})
                    }
                    enriched_candidates.append(enriched_candidate)
            
            except Exception as e:
                logger.warning(f"Ошибка обработки кандидата {candidate.get('doc_id', 'unknown')}: {e}")
                continue
        
        if not enriched_candidates:
            logger.warning(f"ML поиск '{query}': не удалось обогатить ни одного кандидата")
            return []
        
        logger.info(f"ML поиск '{query}': обогащено {len(enriched_candidates)} кандидатов")
        
        ml_ranked_candidates = self.ml_ranker.rank_candidates(query, enriched_candidates)
        
        formatted_results = []
        for candidate in ml_ranked_candidates[:top_n]:
            result = {
                'id': candidate['id'],
                'title': candidate['title'],
                'url': candidate['url'],
                'score': candidate.get('ml_score', candidate['bm25_score']),
                'ml_score': candidate.get('ml_score', candidate['bm25_score']),
                'bm25_score': candidate['bm25_score'],
                'views': candidate.get('views', 0),
                'comments_count': candidate.get('comments_count', 0),
                'tags': candidate.get('tags', []),
                'highlights': candidate.get('highlights', {})
            }
            formatted_results.append(result)
        
        if formatted_results:
            self.redis_manager.cache_search_results(f"ml_{query}", top_n, formatted_results)
        
        search_time = time.time() - start_time
        logger.info(f"ML поиск '{query}': {len(formatted_results)} результатов за {search_time:.3f}с")
        
        return formatted_results
    
    def get_search_stats(self) -> Dict[str, Any]:

        try:
            db_stats = {
                'total_articles': self.db_manager.get_articles_count()
            }
            
            es_stats = self.es_manager.get_index_stats()
            
            ml_stats = self.ml_ranker.get_model_info()
            
            return {
                'database': db_stats,
                'elasticsearch': es_stats,
                'ml_model': ml_stats
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {
                'database': {'total_articles': 0},
                'elasticsearch': {'total_docs': 0},
                'ml_model': {'ready': False}
            }

def get_search_engine() -> SearchEngine:

    global _search_engine
    if _search_engine is None:
        _search_engine = SearchEngine()
    return _search_engine
