import argparse
import logging
from collector import HabrDataCollector
from db_manager import DatabaseManager
from elasticsearch_manager import ElasticsearchManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='Сбор данных с Habr')
    parser.add_argument(
        '--pages', 
        type=int, 
        default=50, 
        help='Количество страниц для сбора (по умолчанию: 50)'
    )
    parser.add_argument(
        '--hub', 
        type=str, 
        help='Собирать статьи только из конкретного хаба (например: python, javascript)'
    )
    parser.add_argument(
        '--test', 
        action='store_true', 
        help='Тестовый режим - собрать только 5 страниц'
    )
    
    args = parser.parse_args()
    
    collector = HabrDataCollector()
    db_manager = DatabaseManager()
    es_manager = ElasticsearchManager()
    
    logger.info("Проверяем подключение к базе данных...")
    if not db_manager.test_connection():
        logger.error("Не удалось подключиться к базе данных!")
        logger.error("Убедитесь, что PostgreSQL запущен и настроен правильно.")
        return
    
    logger.info("Подключение к базе данных успешно!")
    
    pages_to_collect = 5 if args.test else args.pages
    logger.info(f"Начинаем сбор данных с {pages_to_collect} страниц...")
    
    try:
        if args.hub:
            logger.info(f"Собираем статьи из хаба '{args.hub}'...")
            articles = collector.fetch_articles_by_hub(args.hub, pages_to_collect)
        else:
            logger.info("Собираем статьи со всех страниц...")
            articles = collector.fetch_articles(pages_to_collect)
        
        if not articles:
            logger.warning("Не удалось собрать статьи!")
            return
        
        logger.info(f"Собрано {len(articles)} статей")
        
        logger.info("Сохраняем статьи в базу данных...")
        saved_count = db_manager.save_articles_to_db(articles)
        
        logger.info("Индексируем статьи в Elasticsearch...")
        indexed_count = es_manager.reindex_all(articles)
        
        total_count = db_manager.get_articles_count()
        es_stats = es_manager.get_index_stats()
        logger.info(f"Сбор завершен!")
        logger.info(f"Новых статей сохранено: {saved_count}")
        logger.info(f"Всего статей в базе: {total_count}")
        logger.info(f"Проиндексировано в ES: {indexed_count}")
        if es_stats:
            logger.info(f"Размер индекса ES: {es_stats.get('index_size', 0)} байт")
        
        if articles:
            logger.info("\nПримеры собранных статей:")
            for i, article in enumerate(articles[:3], 1):
                logger.info(f"{i}. {article['title']}")
                logger.info(f"   Просмотры: {article['views']}, Рейтинг: {article['score']}")
                logger.info(f"   Теги: {', '.join(article['tags'][:3])}")
                logger.info("")
        
    except KeyboardInterrupt:
        logger.info("Сбор данных прерван пользователем")
    except Exception as e:
        logger.error(f"Ошибка при сборе данных: {e}")
        raise

if __name__ == "__main__":
    main()
