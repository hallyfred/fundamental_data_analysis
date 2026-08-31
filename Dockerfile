FROM apache/airflow:2.9.3-python3.11

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    libpq-dev \
    default-libmysqlclient-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

USER airflow
WORKDIR /opt/airflow

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

ENV PYTHONPATH=/opt/airflow
