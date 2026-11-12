FROM apache/airflow:3.4.0-python3.12

# Libraries our ingestion scripts use (boto3 for AWS, requests for downloads).
# Installing "apache-airflow==3.4.0" alongside stops pip from changing Airflow itself.
RUN pip install --no-cache-dir "apache-airflow==3.4.0" boto3 requests

# dbt gets its own virtual environment, so its libraries can never
# clash with Airflow's libraries.
RUN python -m venv /home/airflow/dbt-venv \
 && /home/airflow/dbt-venv/bin/pip install --no-cache-dir "dbt-core==1.12.6" "dbt-athena==1.11.1"