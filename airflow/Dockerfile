FROM apache/airflow:2.8.0-python3.9

USER root

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

USER airflow

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY src/ /opt/airflow/src/
COPY data/ /opt/airflow/data/

ENV PYTHONPATH="/opt/airflow/src:/opt/airflow:$PYTHONPATH"
