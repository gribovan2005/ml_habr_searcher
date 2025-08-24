import os
import psycopg2
import logging
from typing import List, Dict, Any
from psycopg2.extras import RealDictCursor
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    
    def __init__(self, db_config: Dict[str, str] = None):

        if db_config is None:
            db_config = {
                'host': os.getenv('DB_HOST', 'localhost'),
                'port': os.getenv('DB_PORT', '5433'),
                'database': os.getenv('DB_NAME', 'habr_articles_db'),
                'user': os.getenv('DB_USER', 'habr_user'),
                'password': os.getenv('DB_PASSWORD', 'habr_pass')
            }
        self.db_config = db_config
    
    def get_connection(self):

        return psycopg2.connect(
            host=self.db_config['host'],
            port=self.db_config['port'],
            database=self.db_config['database'],
            user=self.db_config['user'],
            password=self.db_config['password']
        )
    
    def test_connection(self) -> bool:

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    return result[0] == 1
        except Exception as e:
            logger.error(f"Ошибка подключения к базе данных: {e}")
            return False
    
    def save_articles_to_db(self, articles: List[Dict[str, Any]]) -> int:

        if not articles:
            logger.warning("Нет статей для сохранения")
            return 0
        
        saved_count = 0
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    for article in tqdm(articles, desc="Сохранение статей в БД"):
                        try:
                            insert_query = """
                                INSERT INTO articles (url, title, text_content, tags, views, score, comments_count)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (url) DO UPDATE SET
                                    views = EXCLUDED.views,
                                    score = EXCLUDED.score,
                                    comments_count = EXCLUDED.comments_count,
                                    scraped_at = CURRENT_TIMESTAMP
                                RETURNING id
                            """
                            
                            cursor.execute(insert_query, (
                                article['url'],
                                article['title'],
                                article['text_content'],
                                article['tags'],
                                article['views'],
                                article['score'],
                                article['comments_count']
                            ))
                            
                            result = cursor.fetchone()
                            if result:
                                saved_count += 1  
                            
                        except Exception as e:
                            logger.warning(f"Ошибка при сохранении статьи {article.get('id', 'unknown')}: {e}")
                            continue
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Ошибка при работе с базой данных: {e}")
            return 0
        
        logger.info(f"Успешно обработано {saved_count} статей из {len(articles)} (новые + обновленные)")
        return saved_count
    
    def get_articles_count(self) -> int:

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM articles")
                    result = cursor.fetchone()
                    return result[0] if result else 0
        except Exception as e:
            logger.error(f"Ошибка при получении количества статей: {e}")
            return 0
    
    def get_articles_for_search(self) -> List[Dict[str, Any]]:

        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id, url, title, text_content, tags, views, score, comments_count
                        FROM articles
                        ORDER BY scraped_at DESC
                    """)
                    return cursor.fetchall()
        except Exception as e:
            logger.error(f"Ошибка при получении статей для поиска: {e}")
            return []
    
    def get_article_by_id(self, article_id: int) -> Dict[str, Any]:
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id, url, title, text_content, tags, views, score, comments_count, scraped_at
                        FROM articles
                        WHERE id = %s
                    """, (article_id,))
                    return cursor.fetchone()
        except Exception as e:
            logger.error(f"Ошибка при получении статьи {article_id}: {e}")
            return None
    
    def get_article_by_habr_id(self, habr_id: str) -> Dict[str, Any]:
        
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id, url, title, text_content, tags, views, score, comments_count, scraped_at
                        FROM articles
                        WHERE url LIKE %s
                    """, (f'%{habr_id}%',))
                    return cursor.fetchone()
        except Exception as e:
            logger.error(f"Ошибка при получении статьи с Habr ID {habr_id}: {e}")
            return None
    
    def search_articles_by_title(self, search_term: str, limit: int = 10) -> List[Dict[str, Any]]:

        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id, url, title, text_content, tags, views, score, comments_count
                        FROM articles
                        WHERE title ILIKE %s
                        ORDER BY views DESC, score DESC
                        LIMIT %s
                    """, (f'%{search_term}%', limit))
                    return cursor.fetchall()
        except Exception as e:
            logger.error(f"Ошибка при поиске статей: {e}")
            return []
    
    def get_top_articles(self, limit: int = 10) -> List[Dict[str, Any]]:

        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT id, url, title, text_content, tags, views, score, comments_count
                        FROM articles
                        ORDER BY views DESC, score DESC
                        LIMIT %s
                    """, (limit,))
                    return cursor.fetchall()
        except Exception as e:
            logger.error(f"Ошибка при получении топ статей: {e}")
            return []


def main():

    db_manager = DatabaseManager()
    
    if db_manager.test_connection():
        print("Подключение к базе данных успешно!")
        
        count = db_manager.get_articles_count()
        print(f"В базе данных {count} статей")
        
        top_articles = db_manager.get_top_articles(5)
        if top_articles:
            print("\nТоп 5 статей по просмотрам:")
            for i, article in enumerate(top_articles, 1):
                print(f"{i}. {article['title']} (просмотров: {article['views']})")
    else:
        print("Ошибка подключения к базе данных")


if __name__ == "__main__":
    main()
