import sys
import os
sys.path.append('.')

import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import ndcg_score

import joblib
import json
from datetime import datetime
import logging
from typing import Tuple, List, Dict
from db_manager import DatabaseManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RankingModelTrainer:
    
    def __init__(self, mlflow_tracking_uri: str = None):

        self.use_mlflow = False
        try:
            if mlflow_tracking_uri:
                pass  
            self.use_mlflow = False  
            logger.info("MLflow off")
        except Exception as e:
            logger.warning(f"MLflow off")
            self.use_mlflow = False
        
        self.feature_columns = [
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
            'query_length'
        ]
    
    def load_and_prepare_data(self, data_path: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:

        logger.info(f"Загрузка данных из {data_path}...")
        
        df = pd.read_parquet(data_path)
        logger.info(f"Загружено {len(df)} пар запрос-документ")
        
        missing_features = [col for col in self.feature_columns if col not in df.columns]
        if missing_features:
            raise ValueError(f"Отсутствующие признаки: {missing_features}")
        
        if 'relevance_score' not in df.columns:
            raise ValueError("Отсутствует целевая переменная 'relevance_score'")
        
        X = df[self.feature_columns].values
        y = df['relevance_score'].values
        
        df_sorted = df.sort_values('query_id')
        X = df_sorted[self.feature_columns].values
        y = df_sorted['relevance_score'].values
        
        query_counts = df_sorted['query_id'].value_counts().sort_index()
        groups = query_counts.values
        
        logger.info(f"Размер матрицы признаков: {X.shape}")
        logger.info(f"Количество запросов: {len(groups)}")
        logger.info(f"Размер групп: min={groups.min()}, max={groups.max()}, mean={groups.mean():.1f}")
        logger.info(f"Распределение relevance_score: {np.bincount(y.astype(int))}")
        
        return X, y, groups
    
    def split_data_by_queries(self, X: np.ndarray, y: np.ndarray, groups: np.ndarray, 
                            test_size: float = 0.2, random_state: int = 42) -> Tuple:

        logger.info("Разделение данных на train/test по запросам")
        
        n_queries = len(groups)
        query_indices = np.arange(n_queries)
        
        train_query_indices, test_query_indices = train_test_split(
            query_indices, 
            test_size=test_size, 
            random_state=random_state
        )
        
        group_boundaries = np.cumsum(groups)
        group_starts = np.concatenate([[0], group_boundaries[:-1]])
        
        train_doc_indices = []
        train_groups = []
        for query_idx in train_query_indices:
            start = group_starts[query_idx]
            end = group_boundaries[query_idx]
            train_doc_indices.extend(range(start, end))
            train_groups.append(groups[query_idx])
        

        test_doc_indices = []
        test_groups = []
        for query_idx in test_query_indices:
            start = group_starts[query_idx]
            end = group_boundaries[query_idx]
            test_doc_indices.extend(range(start, end))
            test_groups.append(groups[query_idx])
        
        X_train = X[train_doc_indices]
        y_train = y[train_doc_indices]
        groups_train = np.array(train_groups)
        
        X_test = X[test_doc_indices]
        y_test = y[test_doc_indices]
        groups_test = np.array(test_groups)
        
        logger.info(f"Train: {len(X_train)} документов в {len(groups_train)} запросах")
        logger.info(f"Test: {len(X_test)} документов в {len(groups_test)} запросах")
        
        return X_train, X_test, y_train, y_test, groups_train, groups_test
    
    def calculate_ndcg(self, y_true: np.ndarray, y_pred: np.ndarray, 
                      groups: np.ndarray, k: int = 10) -> float:

        ndcg_scores = []
        start_idx = 0
        
        for group_size in groups:
            end_idx = start_idx + group_size
            
            group_true = y_true[start_idx:end_idx]
            group_pred = y_pred[start_idx:end_idx]
            
            if len(group_true) >= k and np.any(group_true > 0):
                ndcg = ndcg_score(
                    group_true.reshape(1, -1),
                    group_pred.reshape(1, -1),
                    k=k
                )
                ndcg_scores.append(ndcg)
            
            start_idx = end_idx
        
        return np.mean(ndcg_scores) if ndcg_scores else 0.0
    
    def train_model(self, X_train: np.ndarray, y_train: np.ndarray, groups_train: np.ndarray,
                   X_test: np.ndarray, y_test: np.ndarray, groups_test: np.ndarray,
                   params: Dict = None) -> lgb.Booster:

        logger.info("Начало обучения LGBMRanker")
        
        if params is None:
            params = {
                'objective': 'lambdarank',
                'metric': 'ndcg',
                'ndcg_eval_at': [5, 10],
                'boosting_type': 'gbdt',
                'num_leaves': 31,
                'learning_rate': 0.05,
                'feature_fraction': 0.9,
                'bagging_fraction': 0.8,
                'bagging_freq': 5,
                'min_data_in_leaf': 20,
                'lambda_l1': 0.0,
                'lambda_l2': 0.0,
                'verbose': -1,
                'random_state': 42
            }
        
        train_data = lgb.Dataset(
            X_train, 
            label=y_train, 
            group=groups_train,
            feature_name=self.feature_columns
        )
        
        valid_data = lgb.Dataset(
            X_test, 
            label=y_test, 
            group=groups_test,
            reference=train_data,
            feature_name=self.feature_columns
        )
        
        model = lgb.train(
            params,
            train_data,
            valid_sets=[valid_data],
            num_boost_round=1000,
            callbacks=[
                lgb.early_stopping(stopping_rounds=50, verbose=True),
                lgb.log_evaluation(period=100, show_stdv=True)
            ]
        )
        
        logger.info(f"Обучение завершено. Лучшая итерация: {model.best_iteration}")
        
        return model
    
    def evaluate_model(self, model: lgb.Booster, X_test: np.ndarray, 
                      y_test: np.ndarray, groups_test: np.ndarray) -> Dict[str, float]:

        logger.info("Оценка качества модели")
        
        y_pred = model.predict(X_test, num_iteration=model.best_iteration)
        
        metrics = {}
        for k in [5, 10, 20]:
            ndcg_k = self.calculate_ndcg(y_test, y_pred, groups_test, k=k)
            metrics[f'ndcg@{k}'] = ndcg_k
            logger.info(f"NDCG@{k}: {ndcg_k:.4f}")
        
        feature_importance = model.feature_importance(importance_type='gain')
        importance_dict = dict(zip(self.feature_columns, feature_importance))
        
        logger.info("\nВажность признаков:")
        sorted_features = sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)
        for feature, importance in sorted_features:
            logger.info(f"  {feature}: {importance}")
        
        return metrics, importance_dict
    
    def run_training_pipeline(self, data_path: str, model_output_path: str = None) -> Dict:

        from contextlib import nullcontext
        context_manager = nullcontext()
        
        with context_manager:
            if self.use_mlflow:
                mlflow.log_param("training_data_path", data_path)
                mlflow.log_param("timestamp", datetime.now().isoformat())
            
            X, y, groups = self.load_and_prepare_data(data_path)
            
            X_train, X_test, y_train, y_test, groups_train, groups_test = \
                self.split_data_by_queries(X, y, groups)
            
            if self.use_mlflow:
                mlflow.log_param("total_documents", len(X))
                mlflow.log_param("total_queries", len(groups))
                mlflow.log_param("train_documents", len(X_train))
                mlflow.log_param("test_documents", len(X_test))
                mlflow.log_param("train_queries", len(groups_train))
                mlflow.log_param("test_queries", len(groups_test))
                mlflow.log_param("features_count", len(self.feature_columns))
            
            model = self.train_model(X_train, y_train, groups_train,
                                   X_test, y_test, groups_test)
            
            metrics, feature_importance = self.evaluate_model(model, X_test, y_test, groups_test)
            
            if self.use_mlflow:
                for metric_name, metric_value in metrics.items():
                    mlflow.log_metric(metric_name, metric_value)
                
                for feature, importance in feature_importance.items():
                    mlflow.log_metric(f"importance_{feature}", importance)
            
            if model_output_path is None:
                model_output_path = '../data/lgbm_ranker_final.pkl'
            
            os.makedirs(os.path.dirname(model_output_path), exist_ok=True)
            joblib.dump(model, model_output_path)
            
            feature_info = {
                'feature_columns': self.feature_columns,
                'feature_importance': feature_importance,
                'metrics': metrics,
                'model_params': model.params
            }
            
            feature_info_path = model_output_path.replace('.pkl', '_info.json')
            with open(feature_info_path, 'w', encoding='utf-8') as f:
                json.dump(feature_info, f, ensure_ascii=False, indent=2)
            
            if self.use_mlflow:
                mlflow.lightgbm.log_model(model, "model")
                mlflow.log_artifact(feature_info_path)
                
                run_id = mlflow.active_run().info.run_id
                logger.info(f"MLflow run ID: {run_id}")
            else:
                logger.info("MLflow недоступен, артефакты сохранены только локально")
                run_id = None
            
            logger.info(f"Модель сохранена в {model_output_path}")
            logger.info(f"Информация о модели сохранена в {feature_info_path}")
            
            return {
                'model_path': model_output_path,
                'feature_info_path': feature_info_path,
                'metrics': metrics,
                'feature_importance': feature_importance,
                'mlflow_run_id': run_id
            }




def main():
    
    logger.info("Запуск обучения ранжирующей модели...")
    
    data_path = '../data/training_features.parquet'
    model_path = '../data/lgbm_ranker_final.pkl'
    
    if not os.path.exists(data_path):
        logger.error(f"Данные не найдены: {data_path}")
        logger.error("Выполните следующие шаги:")
        logger.error("1. Запустите dataset_creation.py")
        logger.error("2. Запустите feature_generator.py")
        return
    
    try:
        trainer = RankingModelTrainer()
    except Exception as mlflow_error:
        trainer = RankingModelTrainer()  
    
    try:
        results = trainer.run_training_pipeline(data_path, model_path)
        

        logger.info("Обучение завершено")
        logger.info(f"Модель: {results['model_path']}")
        
        logger.info("\nМетрики качества:")
        for metric, value in results['metrics'].items():
            logger.info(f"  {metric}: {value:.4f}")
        
        logger.info("\nТоп-5 важных признаков:")
        sorted_features = sorted(results['feature_importance'].items(), 
                               key=lambda x: x[1], reverse=True)
        for i, (feature, importance) in enumerate(sorted_features[:5], 1):
            logger.info(f"  {i}. {feature}: {importance}")

        
    except Exception as e:
        logger.error(f"Ошибка во время обучения: {e}")
        raise


if __name__ == "__main__":
    main()
