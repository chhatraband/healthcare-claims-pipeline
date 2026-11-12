"""
Healthcare claims pipeline: CMS SynPUF -> S3 -> Athena raw tables -> dbt.

Runs the same four steps we ran by hand, in order, with retries.
"""
from datetime import timedelta

import pendulum
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG

PROJECT_DIR = "/opt/airflow/project"           # your project, mounted from Windows
DBT = "/home/airflow/dbt-venv/bin/dbt"          # dbt from its own virtual environment

default_args = {
    "owner": "nikhil",
    "retries": 2,                               # try a failed task 2 more times
    "retry_delay": timedelta(minutes=5),        # wait 5 minutes between tries
}

with DAG(
    dag_id="claims_pipeline",
    description="CMS claims: download -> S3 -> Athena raw tables -> dbt build",
    start_date=pendulum.datetime(2026, 11, 1, tz="America/New_York"),
    schedule="0 6 1 * *",                       # 6:00 AM on the 1st of every month
    catchup=False,                              # don't run for past months
    max_active_runs=1,                          # never two runs at the same time
    default_args=default_args,
    tags=["claims", "aws", "dbt"],
) as dag:

    download_cms_data = BashOperator(
        task_id="download_cms_data",
        bash_command=f"cd {PROJECT_DIR} && python ingestion/download_data.py",
        execution_timeout=timedelta(minutes=30),
    )

    upload_to_s3 = BashOperator(
        task_id="upload_to_s3",
        bash_command=f"cd {PROJECT_DIR} && python ingestion/upload_to_s3.py",
        execution_timeout=timedelta(minutes=30),
    )

    create_athena_raw_tables = BashOperator(
        task_id="create_athena_raw_tables",
        bash_command=f"cd {PROJECT_DIR} && python athena/create_raw_tables.py",
        execution_timeout=timedelta(minutes=15),
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=(
            f"cd {PROJECT_DIR}/claims_dbt && "
            f"{DBT} build --profiles-dir . "
            "--target-path /tmp/dbt/target --log-path /tmp/dbt/logs"
        ),
        execution_timeout=timedelta(minutes=30),
    )

    download_cms_data >> upload_to_s3 >> create_athena_raw_tables >> dbt_build