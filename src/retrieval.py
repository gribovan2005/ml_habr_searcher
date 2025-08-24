import os
import pandas as pd
import numpy as np
from rank_bm25 import BM25Okapi
from pymorphy2 import MorphAnalyzer
import re
from typing import List, Tuple, Dict
import logging
from db_manager import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BM25Retriever:
    def __init__(self, db_config: Dict[str, str] = None):
        self.db_manager = DatabaseManager(db_config)
        self.morph = MorphAnalyzer()
        self.bm25 = None
        self.documents = None
        self.document_ids = None
        self.tokenized_docs = None
        
        self.stopwords = {
            'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то', 'все', 'она',
            'так', 'его', 'но', 'да', 'ты', 'к', 'у', 'же', 'вы', 'за', 'бы', 'по', 'только', 'ее',
            'мне', 'было', 'вот', 'от', 'меня', 'еще', 'нет', 'о', 'из', 'ему', 'теперь', 'когда',
            'даже', 'ну', 'вдруг', 'ли', 'если', 'уже', 'или', 'ни', 'быть', 'был', 'него', 'до',
            'вас', 'нибудь', 'опять', 'уж', 'вам', 'ведь', 'там', 'потом', 'себя', 'ничего', 'ей',
            'может', 'они', 'тут', 'где', 'есть', 'надо', 'ней', 'для', 'мы', 'тебя', 'их', 'чем',
            'была', 'сам', 'чтоб', 'без', 'будто', 'чего', 'раз', 'тоже', 'себе', 'под', 'будет',
            'ж', 'тогда', 'кто', 'этот', 'того', 'потому', 'этого', 'какой', 'совсем', 'ним', 'здесь',
            'этом', 'один', 'почти', 'мой', 'тем', 'чтобы', 'нее', 'сейчас', 'были', 'куда', 'зачем',
            'всех', 'никогда', 'можно', 'при', 'наконец', 'два', 'об', 'другой', 'хоть', 'после',
            'над', 'больше', 'тот', 'через', 'эти', 'нас', 'про', 'всего', 'них', 'какая', 'много',
            'разве', 'три', 'эту', 'моя', 'впрочем', 'хорошо', 'свою', 'этой', 'перед', 'иногда',
            'лучше', 'чуть', 'том', 'нельзя', 'такой', 'им', 'более', 'всегда', 'конечно', 'всю',
            'между'
        }
    
    def load_documents(self):
        try:
            articles = self.db_manager.get_articles_for_search()
            
            if not articles:
                raise ValueError("No articles found in database")
            
            df = pd.DataFrame(articles)
            
            df = df[df['text_content'].notna() & (df['text_content'] != '')]
            
            if df.empty:
                raise ValueError("No articles with valid text content found in database")
            
            self.documents = df
            logger.info(f"Loaded {len(df)} documents from database")
            
        except Exception as e:
            logger.error(f"Error loading documents: {e}")
            raise
    
    def preprocess_text(self, text: str) -> List[str]:
        if not text:
            return []
        
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        
        words = text.split()
        
        processed_words = []
        for word in words:
            if word not in self.stopwords and len(word) > 2:
                parsed = self.morph.parse(word)
                if parsed:
                    lemma = parsed[0].normal_form
                    processed_words.append(lemma)
        
        return processed_words
    
    def fit(self):
        if self.documents is None:
            self.load_documents()
        
        combined_texts = []
        for _, row in self.documents.iterrows():
            title = row['title'] or ''
            text = row['text_content'] or ''
            tags = ' '.join(row['tags']) if row['tags'] else ''
            
            combined = f"{title} {title} {title} {tags} {tags} {text}"
            combined_texts.append(combined)
        
        self.tokenized_docs = [self.preprocess_text(text) for text in combined_texts]
        
        self.document_ids = self.documents['id'].tolist()
        
        self.bm25 = BM25Okapi(self.tokenized_docs)
        
        logger.info(f"BM25 model fitted on {len(self.tokenized_docs)} documents")
    
    def search(self, query: str, top_n: int = 10) -> List[Tuple[int, float]]:
        if self.bm25 is None:
            raise ValueError("Model not fitted. Call fit() first.")
        
        tokenized_query = self.preprocess_text(query)
        
        if not tokenized_query:
            return []
        
        scores = self.bm25.get_scores(tokenized_query)
        
        doc_scores = list(zip(self.document_ids, scores))
        
        doc_scores.sort(key=lambda x: x[1], reverse=True)
        
        return doc_scores[:top_n]
    
    def get_document_by_id(self, doc_id: int) -> pd.Series:
        if self.documents is None:
            raise ValueError("Documents not loaded. Call load_documents() first.")
        
        doc = self.documents[self.documents['id'] == doc_id]
        if doc.empty:
            raise ValueError(f"Document with ID {doc_id} not found")
        
        return doc.iloc[0]
    
    def search_with_details(self, query: str, top_n: int = 10) -> List[Dict]:

        results = self.search(query, top_n)
        
        detailed_results = []
        for doc_id, score in results:
            try:
                doc = self.get_document_by_id(doc_id)
                detailed_results.append({
                    'id': doc_id,
                    'title': doc['title'],
                    'url': doc.get('url', ''),
                    'score': score,
                    'views': doc['views'],
                    'comments_count': doc['comments_count'],
                    'tags': doc['tags']
                })
            except ValueError:
                continue
        
        return detailed_results
