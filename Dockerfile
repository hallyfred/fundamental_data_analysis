FROM apache/airflow:2.9.3-python3.11@sha256:cc5fcb91e93e4dfe4fd8b1b53a9155dfa2670fb829891a9658a0f36ac55f67ef

USER airflow
WORKDIR /opt/airflow

COPY --chown=airflow:root requirements.txt requirements.lock /tmp/
RUN python -m pip install --no-cache-dir --requirement /tmp/requirements.lock && \
    python -m pip check

ENV PYTHONPATH=/opt/airflow
