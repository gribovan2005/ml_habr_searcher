import sys
import os
sys.path.append('.')

import pandas as pd
import numpy as np
import hashlib
from db_manager import DatabaseManager
import logging
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatasetCreator:
    
    def __init__(self, db_manager: DatabaseManager = None):
        self.db_manager = db_manager or DatabaseManager()
        
    def calculate_relevance_score(self, df: pd.DataFrame) -> pd.DataFrame:

        logger.info("Создание relevance_score на основе квантилей метрик")
        
        df = df.copy()
        
        metrics = ['views', 'score', 'comments_count']
        for metric in metrics:
            df[metric] = df[metric].fillna(0)
        
        views_quantiles = df['views'].quantile([0.2, 0.4, 0.6, 0.8]).values
        score_quantiles = df['score'].quantile([0.2, 0.4, 0.6, 0.8]).values
        comments_quantiles = df['comments_count'].quantile([0.2, 0.4, 0.6, 0.8]).values
        
        logger.info(f"Views quantiles: {views_quantiles}")
        logger.info(f"Score quantiles: {score_quantiles}")
        logger.info(f"Comments quantiles: {comments_quantiles}")
        
        def calculate_score(row):
            views = row['views']
            score = row['score']
            comments = row['comments_count']
            
            views_level = np.searchsorted(views_quantiles, views, side='right')
            score_level = np.searchsorted(score_quantiles, score, side='right')
            comments_level = np.searchsorted(comments_quantiles, comments, side='right')
            
            relevance = (0.4 * views_level + 0.4 * score_level + 0.2 * comments_level)
            
            return min(4, int(round(relevance)))
        
        df['relevance_score'] = df.apply(calculate_score, axis=1)
        
        relevance_dist = df['relevance_score'].value_counts().sort_index()
        logger.info(f"Распределение relevance_score:")
        for score, count in relevance_dist.items():
            percentage = count / len(df) * 100
            logger.info(f"  Score {score}: {count} статей ({percentage:.1f}%)")
        
        return df
    
    def generate_query_document_pairs(self, df: pd.DataFrame) -> pd.DataFrame:

        logger.info("Генерация пар запрос-документ из тегов...")
        
        all_tags = set()
        tag_articles = {}  
        
        for idx, row in df.iterrows():
            if row['tags'] and isinstance(row['tags'], list):
                for tag in row['tags']:
                    if tag and isinstance(tag, str) and len(tag.strip()) > 0:
                        tag = tag.strip().lower()
                        all_tags.add(tag)
                        
                        if tag not in tag_articles:
                            tag_articles[tag] = []
                        tag_articles[tag].append(row['id'])
        
        logger.info(f"Найдено {len(all_tags)} уникальных тегов")
        
        min_articles_per_tag = 3
        filtered_tags = {tag: articles for tag, articles in tag_articles.items() 
                        if len(articles) >= min_articles_per_tag}
        
        logger.info(f"После фильтрации осталось {len(filtered_tags)} тегов")
        
        pairs = []
        
        for tag, article_ids in tqdm(filtered_tags.items(), desc="Создание пар запрос-документ"):
            query_id = int(hashlib.md5(tag.encode()).hexdigest()[:8], 16)
            
            for article_id in article_ids:
                article_data = df[df['id'] == article_id].iloc[0]
                
                pairs.append({
                    'query_id': query_id,
                    'query_text': tag,
                    'document_id': article_id,
                    'relevance_score': article_data['relevance_score'],
                    'views': article_data['views'],
                    'score': article_data['score'],
                    'comments_count': article_data['comments_count'],
                    'title': article_data['title'],
                    'text_content': article_data['text_content'],
                    'tags': article_data['tags']
                })
        
        pairs_df = pd.DataFrame(pairs)
        
        logger.info(f"Создано {len(pairs_df)} пар запрос-документ")
        logger.info(f"Количество уникальных запросов: {pairs_df['query_id'].nunique()}")
        
        docs_per_query = pairs_df['query_id'].value_counts()
        logger.info(f"Документов на запрос: min={docs_per_query.min()}, max={docs_per_query.max()}, mean={docs_per_query.mean():.1f}")
        
        return pairs_df
    
    def create_training_dataset(self) -> pd.DataFrame:

        logger.info("Начало создания обучающего датасета...")
        
        logger.info("Загрузка статей из PostgreSQL...")
        
        try:
            with self.db_manager.get_connection() as conn:
                articles_df = pd.read_sql_query("""
                    SELECT id, title, text_content, tags, views, score, comments_count, scraped_at
                    FROM articles 
                    WHERE text_content IS NOT NULL 
                      AND text_content != '' 
                      AND tags IS NOT NULL 
                      AND array_length(tags, 1) > 0
                    ORDER BY scraped_at DESC
                """, conn)
        except Exception as e:
            logger.error(f"Ошибка загрузки данных из БД: {e}")
            raise
        
        logger.info(f"Загружено {len(articles_df)} статей с тегами")
        
        articles_with_relevance = self.calculate_relevance_score(articles_df)
        
        training_pairs = self.generate_query_document_pairs(articles_with_relevance)
        
        logger.info("Обучающий датасет успешно создан!")
        return training_pairs


def main():

    dataset_creator = DatasetCreator()
    training_data = dataset_creator.create_training_dataset()
    
    output_path = '../data/training_dataset.parquet'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    training_data.to_parquet(output_path, index=False)
    logger.info(f"Датасет сохранен в {output_path}")
    logger.info(f"Размер датасета: {training_data.shape}")
    logger.info(f"Столбцы: {list(training_data.columns)}")
    
    logger.info("\nСтатистика обучающего датасета:")
    logger.info(f"Общее количество пар: {len(training_data)}")
    logger.info(f"Уникальных запросов: {training_data['query_id'].nunique()}")
    logger.info(f"Уникальных документов: {training_data['document_id'].nunique()}")
    
    relevance_dist = training_data['relevance_score'].value_counts().sort_index()
    logger.info("Распределение relevance_score:")
    for score, count in relevance_dist.items():
        percentage = count / len(training_data) * 100
        logger.info(f"  Score {score}: {count} пар ({percentage:.1f}%)")
    
    logger.info("\nПримеры запросов:")
    sample_queries = training_data['query_text'].unique()[:5]
    for query in sample_queries:
        query_data = training_data[training_data['query_text'] == query]
        logger.info(f"  '{query}': {len(query_data)} документов")


if __name__ == "__main__":
    main()
