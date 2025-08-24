import os
import json
import logging
import hashlib
from typing import Any, Optional, Dict
import redis

logger = logging.getLogger(__name__)

class RedisManager:
    def __init__(self, host: str = None, port: int = None, db: int = None):
        self.host = host or os.getenv('REDIS_HOST', 'redis')
        self.port = port or int(os.getenv('REDIS_PORT', '6379'))
        self.db = db or int(os.getenv('REDIS_DB', '0'))
        
        try:
            self.redis_client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=True
            )
            
            self.redis_client.ping()
            logger.info("Подключение к Redis установлено")
            
        except redis.ConnectionError as e:
            logger.error(f"Ошибка подключения к Redis: {e}")
            self.redis_client = None
    
    def _generate_cache_key(self, prefix: str, data: Any) -> str:
        data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        data_hash = hashlib.md5(data_str.encode('utf-8')).hexdigest()
        return f"{prefix}:{data_hash}"
    
    def get(self, key: str) -> Optional[Any]:
        if not self.redis_client:
            return None
            
        try:
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Ошибка получения из кэша: {e}")
            return None
    
    def set(self, key: str, value: Any, expire: int = 600) -> bool:
        if not self.redis_client:
            return False
            
        try:
            def json_serializer(obj):
                if hasattr(obj, 'isoformat'):
                    return obj.isoformat()
                raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
            
            data = json.dumps(value, ensure_ascii=False, default=json_serializer)
            self.redis_client.setex(key, expire, data)
            logger.debug(f"Данные сохранены в кэш: {key}")
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения в кэш: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        if not self.redis_client:
            return False
            
        try:
            self.redis_client.delete(key)
            logger.debug(f"Данные удалены из кэша: {key}")
            return True
        except Exception as e:
            logger.error(f"Ошибка удаления из кэша: {e}")
            return False
    
    def cache_search_results(self, query: str, top_n: int, results: list, expire: int = 600) -> bool:
        from datetime import datetime
        
        cache_data = {
            'query': query,
            'top_n': top_n,
            'results': results,
            'cached_at': datetime.now().isoformat()
        }
        
        key = self._generate_cache_key('search', {'query': query, 'top_n': top_n})
        return self.set(key, cache_data, expire)
    
    def get_cached_search_results(self, query: str, top_n: int) -> Optional[list]:
        key = self._generate_cache_key('search', {'query': query, 'top_n': top_n})
        cached_data = self.get(key)
        
        if cached_data and cached_data.get('query') == query:
            logger.info(f"Результаты найдены в кэше для запроса: {query}")
            return cached_data.get('results')
        
        return None
    
    def cache_article_metadata(self, article_id: int, metadata: Dict[str, Any], expire: int = 3600) -> bool:
        key = f"article_meta:{article_id}"
        return self.set(key, metadata, expire)
    
    def get_cached_article_metadata(self, article_id: int) -> Optional[Dict[str, Any]]:
        key = f"article_meta:{article_id}"
        return self.get(key)
    
    def cache_stats(self, stats: Dict[str, Any], expire: int = 1800) -> bool:
        return self.set('stats', stats, expire)
    
    def get_cached_stats(self) -> Optional[Dict[str, Any]]:
        return self.get('stats')
    
    def clear_cache(self, pattern: str = "*") -> bool:
        if not self.redis_client:
            return False
            
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
                logger.info(f"Очищено {len(keys)} ключей кэша")
            return True
        except Exception as e:
            logger.error(f"Ошибка очистки кэша: {e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        if not self.redis_client:
            return {}
            
        try:
            info = self.redis_client.info()
            return {
                'used_memory': info.get('used_memory_human', '0B'),
                'connected_clients': info.get('connected_clients', 0),
                'total_commands_processed': info.get('total_commands_processed', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0)
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики кэша: {e}")
            return {}
