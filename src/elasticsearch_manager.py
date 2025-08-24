import os
import logging
from typing import List, Dict, Any, Optional
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError, NotFoundError

logger = logging.getLogger(__name__)

class ElasticsearchManager:
    def __init__(self, host: str = None, port: int = None):
        self.host = host or os.getenv('ES_HOST', 'elasticsearch')
        self.port = port or int(os.getenv('ES_PORT', '9200'))
        self.index_name = 'habr_articles'
        
        self.es = Elasticsearch([{'host': self.host, 'port': self.port, 'scheme': 'http'}])
        
        try:
            if self.es.ping():
                logger.info("Подключение к Elasticsearch установлено")
                self._create_index_if_not_exists()
            else:
                logger.error("Не удалось подключиться к Elasticsearch")
        except ConnectionError as e:
            logger.error(f"Ошибка подключения к Elasticsearch: {e}")
    
    def _create_index_if_not_exists(self):
        try:
            if not self.es.indices.exists(index=self.index_name):
                mapping = {
                    "mappings": {
                        "properties": {
                            "id": {"type": "integer"},
                            "url": {"type": "keyword"},
                            "title": {
                                "type": "text",
                                "analyzer": "russian",
                                "search_analyzer": "russian"
                            },
                            "text_content": {
                                "type": "text",
                                "analyzer": "russian",
                                "search_analyzer": "russian"
                            },
                            "tags": {
                                "type": "keyword"
                            },
                            "views": {"type": "integer"},
                            "score": {"type": "integer"},
                            "comments_count": {"type": "integer"},
                            "scraped_at": {"type": "date"}
                        }
                    },
                    "settings": {
                        "analysis": {
                            "analyzer": {
                                "russian": {
                                    "type": "custom",
                                    "tokenizer": "standard",
                                    "filter": [
                                        "lowercase",
                                        "russian_stop",
                                        "russian_stemmer"
                                    ]
                                }
                            },
                            "filter": {
                                "russian_stop": {
                                    "type": "stop",
                                    "stopwords": "_russian_"
                                },
                                "russian_stemmer": {
                                    "type": "stemmer",
                                    "language": "russian"
                                }
                            }
                        }
                    }
                }
                
                self.es.indices.create(index=self.index_name, body=mapping)
                logger.info(f"Индекс {self.index_name} создан")
            else:
                logger.info(f"Индекс {self.index_name} уже существует")
                
        except Exception as e:
            logger.error(f"Ошибка создания индекса: {e}")
    
    def index_article(self, article: Dict[str, Any]) -> bool:
        try:
            doc = {
                'id': article['id'],
                'url': article['url'],
                'title': article['title'],
                'text_content': article['text_content'],
                'tags': article['tags'],
                'views': article['views'],
                'score': article['score'],
                'comments_count': article['comments_count'],
                'scraped_at': article.get('scraped_at')
            }
            
            self.es.index(index=self.index_name, id=article['id'], body=doc)
            logger.debug(f"Статья {article['id']} проиндексирована")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка индексации статьи {article.get('id', 'unknown')}: {e}")
            return False
    
    def search_articles(self, query: str, top_n: int = 100) -> List[Dict[str, Any]]:
        try:
            search_query = {
                "multi_match": {
                    "query": query,
                    "fields": [
                        "title^3",
                        "tags^2",
                        "text_content"
                    ],
                    "fuzziness": "AUTO",
                    "type": "best_fields"
                }
            }
            
            response = self.es.search(
                index=self.index_name,
                query=search_query,
                size=top_n,
                highlight={
                    "fields": {
                        "title": {},
                        "text_content": {
                            "fragment_size": 150,
                            "number_of_fragments": 3
                        }
                    }
                }
            )
            
            candidates = []
            for hit in response['hits']['hits']:
                candidate = {
                    'doc_id': int(hit['_id']),
                    'bm25_score': hit['_score'],
                    'title': hit['_source']['title'],
                    'url': hit['_source']['url'],
                    'views': hit['_source']['views'],
                    'comments_count': hit['_source']['comments_count'],
                    'tags': hit['_source']['tags'],
                    'highlights': hit.get('highlight', {})
                }
                candidates.append(candidate)
            
            logger.info(f"Найдено {len(candidates)} кандидатов для запроса '{query}'")
            return candidates
            
        except Exception as e:
            logger.error(f"Ошибка поиска в Elasticsearch: {e}")
            return []
    
    def get_article_by_id(self, doc_id: int) -> Optional[Dict[str, Any]]:
        try:
            response = self.es.get(index=self.index_name, id=doc_id)
            return response['_source']
        except NotFoundError:
            logger.warning(f"Статья с ID {doc_id} не найдена")
            return None
        except Exception as e:
            logger.error(f"Ошибка получения статьи {doc_id}: {e}")
            return None
    
    def get_index_stats(self) -> Dict[str, Any]:
        try:
            stats = self.es.indices.stats(index=self.index_name)
            return {
                'total_docs': stats['indices'][self.index_name]['total']['docs']['count'],
                'index_size': stats['indices'][self.index_name]['total']['store']['size_in_bytes']
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {}
    
    def reindex_all(self, articles: List[Dict[str, Any]]) -> int:
        try:
            if self.es.indices.exists(index=self.index_name):
                self.es.indices.delete(index=self.index_name)
                logger.info("Старый индекс удален")
            
            self._create_index_if_not_exists()
            
            indexed_count = 0
            for article in articles:
                if self.index_article(article):
                    indexed_count += 1
            
            self.es.indices.refresh(index=self.index_name)
            
            logger.info(f"Переиндексация завершена. Проиндексировано {indexed_count} статей")
            return indexed_count
            
        except Exception as e:
            logger.error(f"Ошибка переиндексации: {e}")
            return 0
