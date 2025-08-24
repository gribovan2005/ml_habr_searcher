import sys
import os
sys.path.append('.')

import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List
import re
import logging
from tqdm import tqdm
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FeatureGenerator:
    
    def __init__(self):
        self.tfidf_vectorizer = None
        self.tfidf_matrix = None
        self.document_index = {}  
        
    def generate_document_features(self, df: pd.DataFrame) -> pd.DataFrame:

        logger.info("Генерация признаков документа")
        
        df = df.copy()
        current_time = datetime.now(timezone.utc)
        
        def calculate_freshness(scraped_at):

            if pd.isna(scraped_at):
                return 365  
            
            if isinstance(scraped_at, str):
                try:
                    scraped_date = pd.to_datetime(scraped_at)
                except:
                    return 365
            else:
                scraped_date = scraped_at
                
            if scraped_date.tzinfo is None:
                scraped_date = scraped_date.replace(tzinfo=timezone.utc)
                
            days_diff = (current_time - scraped_date).days
            return max(0, days_diff)
        
        def calculate_word_count(text):

            if pd.isna(text) or text == '':
                return 0

            words = re.findall(r'\w+', str(text).lower())
            return len(words)
        
        def has_code_blocks(text):

            if pd.isna(text):
                return 0
            text_str = str(text)

            code_patterns = [
                r'<code>.*?</code>',
                r'```.*?```',
                r'`.*?`',
                r'<pre>.*?</pre>',
                r'\{.*?\}',
                r'function\s+\w+',
                r'class\s+\w+',
                r'def\s+\w+',
                r'import\s+\w+',
                r'from\s+\w+',
            ]
            for pattern in code_patterns:
                if re.search(pattern, text_str, re.DOTALL | re.IGNORECASE):
                    return 1
            return 0
        
        def has_images(text):

            if pd.isna(text):
                return 0
            text_str = str(text)

            image_patterns = [
                r'<img.*?>',
                r'!\[.*?\]\(.*?\)',
                r'<figure.*?>.*?</figure>',
                r'\.jpg|\.jpeg|\.png|\.gif|\.svg',
            ]
            for pattern in image_patterns:
                if re.search(pattern, text_str, re.IGNORECASE):
                    return 1
            return 0
        

        df['freshness'] = df['views'].apply(lambda x: max(1, 100 - min(99, x // 100)))
        

        df['author_rating'] = df['score'].fillna(0)
        

        df['views'] = df['views'].fillna(0)
        df['comments_count'] = df['comments_count'].fillna(0)
        
        df['article_word_count'] = df['text_content'].apply(calculate_word_count)
        
        df['has_code'] = df['text_content'].apply(has_code_blocks)
        df['has_images'] = df['text_content'].apply(has_images)
        
        df['title_length'] = df['title'].apply(lambda x: len(str(x)) if pd.notna(x) else 0)
        
        df['tags_count'] = df['tags'].apply(lambda x: len(x) if isinstance(x, list) else 0)
        
        logger.info("Признаки документа сгенерированы")
        logger.info(f"  freshness: min={df['freshness'].min():.1f}, max={df['freshness'].max():.1f}")
        logger.info(f"  article_word_count: min={df['article_word_count'].min()}, max={df['article_word_count'].max()}")
        logger.info(f"  has_code: {df['has_code'].mean():.2f} статей имеют код")
        logger.info(f"  has_images: {df['has_images'].mean():.2f} статей имеют изображения")
        
        return df
    
    def generate_query_document_features(self, df: pd.DataFrame) -> pd.DataFrame:

        logger.info("Генерация признаков взаимодействия запрос-документ...")
        
        df = df.copy()
        
        logger.info("Подготовка TF-IDF векторизатора")
        
        documents = []
        unique_docs = df.drop_duplicates(subset=['document_id'])
        
        for _, row in unique_docs.iterrows():
            title = str(row['title']) if pd.notna(row['title']) else ''
            text_content = str(row['text_content'])[:500] if pd.notna(row['text_content']) else ''
            doc_text = f"{title} {text_content}".strip()
            documents.append(doc_text)
            self.document_index[row['document_id']] = len(documents) - 1
        
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.8,
            stop_words=None,  
            lowercase=True
        )
        
        self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(documents)
        logger.info(f"TF-IDF матрица: {self.tfidf_matrix.shape}")
        
        def calculate_tfidf_similarity(query_text, document_id):

            try:
                doc_idx = self.document_index[document_id]
                doc_vec = self.tfidf_matrix[doc_idx:doc_idx+1]
                
                query_vec = self.tfidf_vectorizer.transform([str(query_text)])
                
                similarity = cosine_similarity(query_vec, doc_vec)[0, 0]
                return similarity
            except:
                return 0.0
        
        def preprocess_text(text):

            if pd.isna(text):
                return ''
            text = str(text).lower()
            text = re.sub(r'[^\w\s]', ' ', text)
            words = text.split()
            return set(word for word in words if len(word) > 2)
        
        def query_in_title(query_text, title):

            query_words = preprocess_text(query_text)
            title_words = preprocess_text(title)
            
            if not query_words or not title_words:
                return 0
                
            intersection = query_words.intersection(title_words)
            return 1 if len(intersection) > 0 else 0
        
        def query_in_tags(query_text, tags):

            if not isinstance(tags, list) or not tags:
                return 0
                
            query_lower = str(query_text).lower().strip()
            for tag in tags:
                if query_lower == str(tag).lower().strip():
                    return 1
            return 0
        
        def calculate_text_overlap(query_text, text_content):

            query_words = preprocess_text(query_text)
            text_words = preprocess_text(text_content[:1000])  
            
            if not query_words or not text_words:
                return 0
                
            intersection = query_words.intersection(text_words)
            if len(query_words) == 0:
                return 0
            return len(intersection) / len(query_words)
        
        logger.info("Вычисление TF-IDF similarity")
        tqdm.pandas(desc="TF-IDF similarity")
        df['tfidf_similarity'] = df.progress_apply(
            lambda row: calculate_tfidf_similarity(row['query_text'], row['document_id']), 
            axis=1
        )
        
        logger.info("Вычисление остальных признаков взаимодействия")
        df['query_in_title'] = df.apply(lambda row: query_in_title(row['query_text'], row['title']), axis=1)
        df['query_in_tags'] = df.apply(lambda row: query_in_tags(row['query_text'], row['tags']), axis=1)
        df['text_overlap_ratio'] = df.apply(lambda row: calculate_text_overlap(row['query_text'], row['text_content']), axis=1)
        
        df['query_length'] = df['query_text'].apply(lambda x: len(str(x).split()))
        
        df['bm25_score'] = 0.0
        
        logger.info("Признаки взаимодействия сгенерированы")
        logger.info(f"  tfidf_similarity: min={df['tfidf_similarity'].min():.3f}, max={df['tfidf_similarity'].max():.3f}")
        logger.info(f"  query_in_title: {df['query_in_title'].mean():.3f} пар имеют запрос в заголовке")
        logger.info(f"  query_in_tags: {df['query_in_tags'].mean():.3f} пар имеют точное совпадение с тегом")
        logger.info(f"  text_overlap_ratio: mean={df['text_overlap_ratio'].mean():.3f}")
        
        return df
    
    def generate_all_features(self, input_path: str, output_path: str):

        logger.info(f"Загрузка датасета из {input_path}...")
        
        df = pd.read_parquet(input_path)
        logger.info(f"Загружено {len(df)} пар запрос-документ")
        
        df = self.generate_document_features(df)
        
        df = self.generate_query_document_features(df)
        
        feature_columns = [
            'freshness',
            'author_rating', 
            'views',
            'comments_count',
            'article_word_count',
            'has_code',
            'has_images',
            'title_length',
            'tags_count',
            
            'tfidf_similarity',
            'query_in_title',
            'query_in_tags', 
            'text_overlap_ratio',
            'query_length',
            'bm25_score'  
        ]
        
        missing_features = [col for col in feature_columns if col not in df.columns]
        if missing_features:
            logger.error(f"Отсутствующие признаки: {missing_features}")
            raise ValueError(f"Отсутствующие признаки: {missing_features}")
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_parquet(output_path, index=False)
        
        tfidf_path = os.path.join(os.path.dirname(output_path), 'tfidf_vectorizer.pkl')
        with open(tfidf_path, 'wb') as f:
            pickle.dump({
                'vectorizer': self.tfidf_vectorizer,
                'document_index': self.document_index
            }, f)
        
        logger.info(f"Датасет с признаками сохранен в {output_path}")
        logger.info(f"TF-IDF векторизатор сохранен в {tfidf_path}")
        logger.info(f"Финальный размер датасета: {df.shape}")
        logger.info(f"Признаки: {feature_columns}")
        
        logger.info("\nСтатистика по признакам:")
        for col in feature_columns:
            if col in df.columns:
                logger.info(f"  {col}: min={df[col].min():.3f}, max={df[col].max():.3f}, mean={df[col].mean():.3f}")
        
        return df


def main():
    
    input_path = '../data/training_dataset.parquet'
    output_path = '../data/training_features.parquet'
    
    if not os.path.exists(input_path):
        logger.error(f"Датасет не найден: {input_path}")
        logger.error("Сначала запустите dataset_creation.py")
        return
    
    feature_generator = FeatureGenerator()
    feature_generator.generate_all_features(input_path, output_path)
    
    logger.info("Генерация признаков завершена успешно!")


if __name__ == "__main__":
    main()
