import logging
from db_manager import DatabaseManager
from elasticsearch_manager import ElasticsearchManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    logger.info("Начинаем индексацию данных в Elasticsearch...")
    
    db_manager = DatabaseManager()
    es_manager = ElasticsearchManager()
    
    logger.info("Проверяем подключение к базе данных")
    if not db_manager.test_connection():
        logger.error("Не удалось подключиться к базе данных")
        return
    
    logger.info("Подключение к базе данных успешно")
    
    logger.info("Загружаем статьи из базы данных")
    articles = db_manager.get_articles_for_search()
    
    if not articles:
        logger.warning("Нет статей для индексации")
        return
    
    logger.info(f"Найдено {len(articles)} статей для индексации")
    
    logger.info("Индексируем статьи в Elasticsearch")
    indexed_count = es_manager.reindex_all(articles)
    
    es_stats = es_manager.get_index_stats()
    
    logger.info("Индексация завершена")
    logger.info(f"Проиндексировано статей: {indexed_count}")
    if es_stats:
        logger.info(f"Всего документов в индексе: {es_stats.get('total_docs', 0)}")
        logger.info(f"Размер индекса: {es_stats.get('index_size', 0)} байт")


if __name__ == "__main__":
    main()
