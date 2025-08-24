import os
import sys
import json
import pickle
import joblib
import logging
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MLRanker:    
    def __init__(self, model_path: str = None, feature_info_path: str = None, 
                 tfidf_path: str = None):
        
        data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
        
        if model_path is None:
            model_path = os.path.join(data_dir, 'lgbm_ranker_final.pkl')
        if feature_info_path is None:
            feature_info_path = os.path.join(data_dir, 'lgbm_ranker_final_info.json')
        if tfidf_path is None:
            tfidf_path = os.path.join(data_dir, 'tfidf_vectorizer.pkl')
        
        self.model = None
        self.feature_columns = None
        self.tfidf_vectorizer = None
        self.tfidf_document_index = None
        
        try:
            import joblib
            self.model = joblib.load(model_path)
            logger.info(f"LightGBM модель загружена из {model_path}")
        except FileNotFoundError:
            logger.warning(f"Модель не найдена: {model_path}")
            self.model = None
        except Exception as e:
            logger.error(f"Ошибка загрузки модели: {e}")
            self.model = None
        
        try:
            with open(feature_info_path, 'r', encoding='utf-8') as f:
                feature_info = json.load(f)
                self.feature_columns = feature_info.get('feature_columns', [])
            logger.info(f"Информация о признаках загружена из {feature_info_path}")
        except FileNotFoundError:
            logger.warning(f"Информация о признаках не найдена: {feature_info_path}")
            self.feature_columns = [
                'freshness', 'author_rating', 'views', 'comments_count',
                'article_word_count', 'has_code', 'has_images', 'title_length',
                'tags_count', 'tfidf_similarity', 'query_in_title', 
                'query_in_tags', 'text_overlap_ratio', 'query_length'
            ]
        except Exception as e:
            logger.error(f"Ошибка загрузки информации о признаках: {e}")
            self.feature_columns = []
        
        try:
            with open(tfidf_path, 'rb') as f:
                tfidf_data = pickle.load(f)
                self.tfidf_vectorizer = tfidf_data.get('vectorizer')
                self.tfidf_document_index = tfidf_data.get('document_index', {})
            logger.info(f"TF-IDF векторизатор загружен из {tfidf_path}")
        except FileNotFoundError:
            logger.warning(f"TF-IDF векторизатор не найден: {tfidf_path}")
            self.tfidf_vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
        except Exception as e:
            logger.error(f"Ошибка загрузки TF-IDF векторизатора: {e}")
            self.tfidf_vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
    
    def is_ready(self) -> bool:
        return self.model is not None and bool(self.feature_columns)
    
    def generate_document_features(self, doc: Dict[str, Any]) -> Dict[str, float]:
        
        def calculate_word_count(text):
            if not text:
                return 0
            words = re.findall(r'\w+', str(text).lower())
            return len(words)
        
        def has_code_blocks(text):
            if not text:
                return 0
            text_str = str(text)
            code_patterns = [
                r'<code>.*?</code>', r'```.*?```', r'`.*?`', r'<pre>.*?</pre>',
                r'\{.*?\}', r'function\s+\w+', r'class\s+\w+', r'def\s+\w+',
                r'import\s+\w+', r'from\s+\w+'
            ]
            for pattern in code_patterns:
                if re.search(pattern, text_str, re.DOTALL | re.IGNORECASE):
                    return 1
            return 0
        
        def has_images(text):
            if not text:
                return 0
            text_str = str(text)
            image_patterns = [
                r'<img.*?>', r'!\[.*?\]\(.*?\)', r'<figure.*?>.*?</figure>',
                r'\.jpg|\.jpeg|\.png|\.gif|\.svg'
            ]
            for pattern in image_patterns:
                if re.search(pattern, text_str, re.IGNORECASE):
                    return 1
            return 0
        
        views = doc.get('views', 0) or 0
        text_content = doc.get('text_content', '') or ''
        title = doc.get('title', '') or ''
        tags = doc.get('tags', []) or []
        
        query_words = set(query.lower().split())
        title_words = set(title.lower().split())
        tag_words = set(' '.join(tags).lower().split())
        
        common_words_count = len(query_words.intersection(title_words))
        tag_overlap_count = len(query_words.intersection(tag_words))
        
        features = {
            'views': views,
            'comments_count': doc.get('comments_count', 0) or 0,
            'score': doc.get('score', 0) or 0,
            'text_length': calculate_word_count(text_content),
            'query_in_title': 1 if query.lower() in title.lower() else 0,
            'common_words': common_words_count,
            'tag_overlap': tag_overlap_count,
            'bm25_score': doc.get('bm25_score', 0) or 0
        }
        
        return features
    
    def generate_query_document_features(self, query: str, doc: Dict[str, Any], 
                                       bm25_score: float = 0.0) -> Dict[str, float]:
        
        def preprocess_text(text):
            if not text:
                return set()
            text = str(text).lower()
            text = re.sub(r'[^\w\s]', ' ', text)
            words = text.split()
            return set(word for word in words if len(word) > 2)
        
        def calculate_tfidf_similarity(query_text, doc_text):
            
            if not self.tfidf_vectorizer:
                return 0.0
            
            try:
                texts = [str(query_text), str(doc_text)]
                
                if not hasattr(self.tfidf_vectorizer, 'vocabulary_') or \
                   self.tfidf_vectorizer.vocabulary_ is None:
                    tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
                else:
                    tfidf_matrix = self.tfidf_vectorizer.transform(texts)
                
                query_vec = tfidf_matrix[0:1]
                doc_vec = tfidf_matrix[1:2]
                similarity = cosine_similarity(query_vec, doc_vec)[0, 0]
                
                return float(similarity)
            except:
                return 0.0
        
        query_lower = str(query).lower().strip()
        title = str(doc.get('title', ''))
        text_content = str(doc.get('text_content', ''))[:1000]  
        tags = doc.get('tags', []) or []
        
        query_words = preprocess_text(query)
        title_words = preprocess_text(title)
        text_words = preprocess_text(text_content)
        
        doc_text = f"{title} {text_content}"
        tfidf_similarity = calculate_tfidf_similarity(query, doc_text)
        
        query_in_title = 1 if len(query_words.intersection(title_words)) > 0 else 0
        
        query_in_tags = 0
        for tag in tags:
            if query_lower == str(tag).lower().strip():
                query_in_tags = 1
                break
        
        text_overlap_ratio = 0.0
        if query_words and text_words:
            intersection = query_words.intersection(text_words)
            text_overlap_ratio = len(intersection) / len(query_words)
        
        features = {
            'tfidf_similarity': tfidf_similarity,
            'query_in_title': query_in_title,
            'query_in_tags': query_in_tags,
            'text_overlap_ratio': text_overlap_ratio,
            'query_length': len(str(query).split())
        }
        
        return features
    
    def generate_features_for_candidate(self, query: str, doc: Dict[str, Any], 
                                      bm25_score: float = 0.0) -> List[float]:
        
        views = doc.get('views', 0) or 0
        comments_count = doc.get('comments_count', 0) or 0
        score = doc.get('score', 0) or 0
        text_content = doc.get('text_content', '') or ''
        title = doc.get('title', '') or ''
        tags = doc.get('tags', []) or []
        
        text_length = len(text_content.split()) if text_content else 0
        
        tfidf_similarity = 0.0
        if self.tfidf_vectorizer and text_content:
            try:
                query_vec = self.tfidf_vectorizer.transform([query])
                doc_vec = self.tfidf_vectorizer.transform([f"{title} {text_content}"])
                similarity = (query_vec * doc_vec.T).toarray()[0][0]
                tfidf_similarity = float(similarity)
            except Exception as e:
                logger.debug(f"Ошибка вычисления TF-IDF: {e}")
        
        query_in_title = 1 if query.lower() in title.lower() else 0
        
        query_words = set(query.lower().split())
        title_words = set(title.lower().split())
        common_words = len(query_words.intersection(title_words))
        
        tag_words = set(' '.join(tags).lower().split()) if tags else set()
        tag_overlap = len(query_words.intersection(tag_words))
        
        feature_vector = [
            float(views),
            float(comments_count), 
            float(score),
            float(text_length),
            float(tfidf_similarity),
            float(query_in_title),
            float(common_words),
            float(tag_overlap),
            float(bm25_score)
        ]
        
        return feature_vector
    
    def rank_candidates(self, query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:

        if not self.is_ready():
            logger.warning("ML модель не готова, возвращаем исходный порядок")
            for candidate in candidates:
                candidate['ml_score'] = candidate.get('bm25_score', 0.0)
            return candidates
        
        if not candidates:
            return []
        
        try:
            features_matrix = []
            valid_candidates = []
            
            for candidate in candidates:
                try:
                    features = self.generate_features_for_candidate(
                        query, 
                        candidate, 
                        candidate.get('bm25_score', 0.0)
                    )
                    
                    if features and len(features) == len(self.feature_columns):
                        features_matrix.append(features)
                        valid_candidates.append(candidate)
                except Exception as e:
                    logger.warning(f"Ошибка генерации признаков для кандидата {candidate.get('id', 'unknown')}: {e}")
                    continue
            
            if not features_matrix:
                logger.warning("Не удалось сгенерировать признаки ни для одного кандидата")
                for candidate in candidates:
                    candidate['ml_score'] = candidate.get('bm25_score', 0.0)
                return candidates
            
            features_array = np.array(features_matrix)
            ml_scores = self.model.predict(features_array, num_iteration=self.model.best_iteration)
            
            for i, candidate in enumerate(valid_candidates):
                candidate['ml_score'] = float(ml_scores[i])
            
            valid_candidates.sort(key=lambda x: x['ml_score'], reverse=True)
            
            logger.info(f"Успешно ранжированы {len(valid_candidates)} кандидатов")
            return valid_candidates
            
        except Exception as e:
            logger.error(f"Ошибка при ранжировании кандидатов: {e}")
            for candidate in candidates:
                candidate['ml_score'] = candidate.get('bm25_score', 0.0)
            return candidates
    
    def get_model_info(self) -> Dict[str, Any]:

        return {
            'model_loaded': self.model is not None,
            'features_count': len(self.feature_columns) if self.feature_columns else 0,
            'feature_columns': self.feature_columns,
            'tfidf_loaded': self.tfidf_vectorizer is not None,
            'ready': self.is_ready()
        }
