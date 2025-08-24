from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
import sys
import os

sys.path.append('/opt/airflow/src')

from collector import HabrDataCollector
from db_manager import DatabaseManager
from elasticsearch_manager import ElasticsearchManager

default_args = {
    'owner': 'habr-search',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

def collect_articles(**context):
    print("Запускаем сбор статей с Habr")
    
    collector = HabrDataCollector()
    
    pages = context.get('dag_run').conf.get('pages', 10) if context.get('dag_run') and context.get('dag_run').conf else 10
    
    print(f"Собираем статьи с {pages} страниц")
    articles = collector.fetch_articles(pages)
    
    if not articles:
        raise Exception("Не удалось собрать статьи")
    
    print(f"Собрано {len(articles)} статей")
    
    context['task_instance'].xcom_push(key='articles', value=articles)
    context['task_instance'].xcom_push(key='articles_count', value=len(articles))
    
    return len(articles)

def save_to_database(**context):
    print("Сохраняем статьи в базу данных")
    
    articles = context['task_instance'].xcom_pull(key='articles', task_ids='collect_articles')
    if not articles:
        raise Exception("Нет статей для сохранения")
    
    db_manager = DatabaseManager()
    
    if not db_manager.test_connection():
        raise Exception("Не удалось подключиться к базе данных")
    
    saved_count = db_manager.save_articles_to_db(articles)
    total_count = db_manager.get_articles_count()
    
    print(f"Сохранено {saved_count} новых статей")
    print(f"Всего статей в базе: {total_count}")
    
    context['task_instance'].xcom_push(key='saved_count', value=saved_count)
    context['task_instance'].xcom_push(key='total_count', value=total_count)
    
    return saved_count

def index_elasticsearch(**context):
    print("Индексируем статьи в Elasticsearch")
    
    articles = context['task_instance'].xcom_pull(key='articles', task_ids='collect_articles')
    if not articles:
        raise Exception("Нет статей для индексирования")
    
    es_manager = ElasticsearchManager()
    
    indexed_count = es_manager.reindex_all(articles)
    es_stats = es_manager.get_index_stats()
    
    print(f"Проиндексировано {indexed_count} статей")
    if es_stats:
        print(f"Размер индекса: {es_stats.get('index_size', 0)} байт")
    
    context['task_instance'].xcom_push(key='indexed_count', value=indexed_count)
    
    return indexed_count

def check_data_quality(**context):
    print("Проверяем качество данных")
    
    saved_count = context['task_instance'].xcom_pull(key='saved_count', task_ids='save_to_database')
    indexed_count = context['task_instance'].xcom_pull(key='indexed_count', task_ids='index_elasticsearch')
    total_count = context['task_instance'].xcom_pull(key='total_count', task_ids='save_to_database')
    articles_count = context['task_instance'].xcom_pull(key='articles_count', task_ids='collect_articles')
    
    print(f"Статистика выполнения:")
    print(f"   Собрано статей: {articles_count}")
    print(f"   Сохранено новых: {saved_count}")
    print(f"   Проиндексировано: {indexed_count}")
    print(f"   Всего в базе: {total_count}")
    
    if articles_count == 0:
        raise Exception("Не собрано ни одной статьи")
    
    if saved_count == 0:
        print("Предупреждение: Не сохранено новых статей (возможно, все уже были в базе)")
    
    if indexed_count != articles_count:
        print(f"Предупреждение: Проиндексировано {indexed_count} из {articles_count} статей")
    
    print("Проверка качества данных завершена")
    return True

dag = DAG(
    'habr_etl_pipeline',
    default_args=default_args,
    description='ETL пайплайн для сбора и обработки статей с Habr',
    schedule_interval=timedelta(hours=6), 
    max_active_runs=1, 
    catchup=False, 
    tags=['habr', 'etl', 'data-collection'],
)

check_services = BashOperator(
    task_id='check_services',
    bash_command='''
    echo "Проверка доступности сервисов"
    
    until pg_isready -h postgres_articles -p 5432 -U habr_user; do
        echo "Ожидаем PostgreSQL"
    done
    echo "PostgreSQL доступен"
    
    until curl -s http://elasticsearch:9200/_cluster/health > /dev/null; do
        echo "Ожидаем Elasticsearch"
    done
    echo "Elasticsearch доступен"
    
    until nc -z redis 6379; do
        echo "ждем Redis"
    done
    echo "Redis доступен"
    
    echo "Все сервисы готовы"
    ''',
    dag=dag,
)

collect_task = PythonOperator(
    task_id='collect_articles',
    python_callable=collect_articles,
    dag=dag,
)

save_task = PythonOperator(
    task_id='save_to_database',
    python_callable=save_to_database,
    dag=dag,
)

index_task = PythonOperator(
    task_id='index_elasticsearch',
    python_callable=index_elasticsearch,
    dag=dag,
)

quality_check_task = PythonOperator(
    task_id='check_data_quality',
    python_callable=check_data_quality,
    dag=dag,
)

check_services >> collect_task >> [save_task, index_task] >> quality_check_task
