# Habr Searcher

Интеллектуальная поисковая система(прототип/демо) для статей с Habr.com с ML-ранжированием и двухэтапным поиском

## Описание проекта

Это  система поиска статей с Habr.com, которая объединяет классические методы поиска (BM25) с машинным обучением (LightGBM Ranker) для улучшения релевантности результатов поиска

### Ключевые особенности

- **Два этапа поиска**: Быстрый поиск через Elasticsearch + ML-ранжирование
- **Автоматизированный сбор данных**: ETL пайплайн на Apache Airflow каждые 6 часов
- **Веб-интерфейс**: React приложение
- **Микросервисная архитектура**: Docker-compose с масштабируемыми компонентами
- **Мониторинг и логирование**: Prometheus, Grafana, MLflow(не интегрировано пока)
- **Кеширование**: Redis для оптимизации производительности

## Архитектура системы

### Компоненты

1. **Сбор данных (data collection)**
   - `collector.py` - Скрапер статей с Habr.com через RSS и веб-скрапинг

2. **Хранение данных (data storage)**
   - **PostgreSQL** - Основная база данных статей
   - **Elasticsearch** - Индекс для полнотекстового поиска
   - **Redis** - Кеширование результатов поиска

3. **ML Pipeline**
   - `feature_generator.py` - Генерация признаков для ML модели
   - `train.py` - Обучение LGBMRanker модели
   - `ml_ranker.py` - ранжирование
   - Поддержка MLflow для трекинга экспериментов(пока не интегрировано)

4. **API (FastAPI)**
   - `api/app/main.py` - Основной FastAPI сервер
   - `search_engine.py` - Двухэтапный поисковый движок
   - REST API с OpenAPI документацией

5. **Frontend (React)**
   - Современный интерфейс на React + Tailwind CSS
   - Сравнение результатов BM25 vs ML-ранжирование

6. **ETL Pipeline (Apache Airflow)**
   - `airflow/dags/habr_etl_dag.py` - DAG для автоматизации сбора данных
   - сбор новых статей
   - Контроль качества данных

7. **Мониторинг**
   - **Prometheus** - Метрики системы
   - **Grafana** - Дашборды мониторинга
   - **MLflow** - Трекинг ML экспериментов(пока не интегрировано)

## Технический стек

### Backend
- **Python 3.9+**
- **FastAPI** - Фреймворк
- **LightGBM** - ML модель для ранжирования
- **Apache Airflow** - ETL
- **Elasticsearch** - Поисковый индекс
- **PostgreSQL** - База данных
- **Redis** - Кеширование

### Frontend
- **React** - Фронт фреймворк
- **Tailwind CSS** - Стили
- **Axios** - HTTP клиент

### DevOps
- **Docker & Docker Compose** - Контейнеризация
- **Prometheus** - Мониторинг метрик
- **Grafana** - Визуализация
- **MLflow** - ML Operations :(


## API эндпойнты

### Основные эндпоинты

```bash

POST /api/search

GET /api/stats

GET /api/top-articles

GET /api/articles/hub/{hub_name}

GET /api/ml-model/status
```

### Пример для python

```python
import requests

response = requests.post("http://localhost:8000/api/search", json={
    "query": "Python FastAPI",
    "top_n": 5,
    "compare": False
})

response = requests.post("http://localhost:8000/api/search", json={
    "query": "машинное обучение",
    "top_n": 10,
    "compare": True
})
```


## ML Pipeline

### Обучение модели

```bash
python run_ml_pipeline.py
or
cd src
python dataset_creation.py    
python feature_generator.py  
python train.py            
```

### Признаки модели

ML модель использует следующие группы признаков:

1. **Текстовые признаки**
   - TF-IDF косинусное сходство заголовка и запроса
   - Длина заголовка и контента
   - Количество слов в пересечении

2. **Статистические признаки**
   - Количество просмотров
   - Рейтинг статьи
   - Количество комментариев

3. **Временные признаки**
   - Возраст статьи
   - День недели публикации

4. **BM25 признаки**
   - BM25 скор по заголовку
   - BM25 скор по содержанию

## ETL Process

Airflow DAG `habr_etl_pipeline` выполняет следующие шаги:

1. **check_services** - Проверка доступности сервисов
2. **collect_articles** - Сбор статей с Habr
3. **save_to_database** - Сохранение в PostgreSQL
4. **index_elasticsearch** - Индексирование в Elasticsearch
5. **check_data_quality** - Контроль качества данных

Пайплайн запускается каждые 6 часов автоматически.

## Мониторинг

### Метрики

- Время ответа API
- Количество запросов в секунду
- Статус сервисов
- Размер индексов
- ML метрики (NDCG, точность)

## Производительность

### Оптимизации

- **Кеширование**: Redis кеш для частых запросов
- **Индексация**: Оптимизированные индексы PostgreSQL и Elasticsearch


## Безопасность

- CORS настроен для разрешенных доменов
- Валидация входных данных через Pydantic
- Rate limiting через Redis
