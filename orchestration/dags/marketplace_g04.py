"""Group 4's nightly pipeline: database to bronze, bronze to silver and gold.

    extract_<table> (x7) >> recreate_live_tables >> source_freshness >> dbt_build

The DAG only says what runs and in what order. Every task is a container from
our own images (ADR 0006), so nothing here reads a database or a table.

* extract_<table>: the extractor, full batch, writes bronze/postgres/<table>/.
* recreate_live_tables: reruns ingestion/extract_external_tables.sql, so the
  seven <table>_live tables, and dbt's freshness check, see the new files.
* source_freshness: dbt source freshness. Fails when a source is past its
  error threshold, for example the clickstream when its consumer has stopped.
* dbt_build: models and tests together. A failed test skips everything
  downstream of it, so a bad number never reaches gold: the quality gate.

The clickstream is not a task: its consumer is a service of its own
(ingestion/compose.yaml, ADR 0003). The DAG only checks that it is fresh.

Paths are the HOST's: a task asks the laptop's Docker to start a container
beside Airflow. They come from orchestration/.env through Compose.
"""

import json
import os
import urllib.request

import pendulum
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.sdk import DAG
from docker.types import Mount

REPO_DIR = os.environ["REPO_DIR"]
GCLOUD_DIR = os.environ["GCLOUD_DIR"]
ALERT_WEBHOOK = os.environ.get("ALERT_WEBHOOK", "")

# The images, pinned by tag (ADR 0006). Change the tag here, nowhere else.
TAG = "20261118-796cf3e"
INGESTION_IMAGE = f"docker.io/jgalthie/group4-ingestion:{TAG}"
TRANSFORM_IMAGE = f"docker.io/jgalthie/group4-transform:{TAG}"

# The local company database, from inside the marketplace stack's network.
# These are the stack's own default credentials, the same as in the course.
DATABASE_URL = "postgresql://postgres:postgres@db:5432/marketplace"

TABLES = ["orders", "order_items", "review", "product_reviews", "product",
          "customer_shipping", "shipping_details"]

# Your own Google login, read only. No service account, no key file.
adc = Mount(source=f"{GCLOUD_DIR}/application_default_credentials.json",
            target="/gcloud/adc.json", type="bind", read_only=True)
GOOGLE_ENV = {
    "GOOGLE_APPLICATION_CREDENTIALS": "/gcloud/adc.json",
    "GOOGLE_CLOUD_PROJECT": "data-engineering-i1",
}
# The SQL that recreates the _live tables, read only, from the repo.
live_sql = Mount(source=f"{REPO_DIR}/ingestion/extract_external_tables.sql",
                 target="/sql/extract_external_tables.sql", type="bind", read_only=True)

# Run the SQL file with the BigQuery client already in the dbt image, so no
# third image is needed. One script, one job: the seven statements together.
RECREATE = (
    "from google.cloud import bigquery; "
    "sql = open('/sql/extract_external_tables.sql').read(); "
    "job = bigquery.Client(location='europe-west1').query(sql); job.result(); "
    "print('recreated the _live tables, job', job.job_id)"
)


def alert(context):
    """Called once, when a task has failed for the last time (after retries).

    Prints the alert into the task's log, then posts it to the group's
    Discord channel. A failed post must not hide the original failure, so it
    is caught and printed.
    """
    ti = context["task_instance"]
    text = (f"ALERT {ti.dag_id}.{ti.task_id} failed for "
            f"{context['data_interval_start']:%Y-%m-%d} after {ti.try_number} tries. "
            f"Runbook: docs/runbooks/failed-run.md")
    print(text, flush=True)
    if not ALERT_WEBHOOK:
        print("ALERT_WEBHOOK is not set: no Discord message", flush=True)
        return
    try:
        req = urllib.request.Request(
            ALERT_WEBHOOK, data=json.dumps({"content": text}).encode(),
            headers={"Content-Type": "application/json", "User-Agent": "group4-airflow"})
        urllib.request.urlopen(req, timeout=10)
    except Exception as exc:  # the alert must never raise
        print(f"Discord post failed: {exc}", flush=True)


def container(task_id, image, **kwargs):
    """A DockerOperator with the settings every task shares."""
    return DockerOperator(
        task_id=task_id,
        image=image,
        # Never pull at run time: the image is pinned and already on the host.
        force_pull=False,
        # Keep a failed container, so `docker logs` still works after Airflow
        # has moved on. Remove it when it succeeds.
        auto_remove="success",
        mount_tmp_dir=False,
        **kwargs,
    )


with DAG(
    dag_id="g04_marketplace_daily",
    # 02:00 UTC, after the day it covers has ended.
    schedule="0 2 * * *",
    start_date=pendulum.datetime(2026, 11, 1, tz="UTC"),
    # No automatic catch-up when the DAG is switched on: a back-fill is run on
    # purpose, with `airflow backfill create` (docs/orchestration.md).
    catchup=False,
    # Two runs would extract into the same files at the same time.
    max_active_runs=1,
    # At most two containers at once: the laptop has 5 GB for Docker.
    max_active_tasks=2,
    default_args={
        # Three attempts in all. Each extractor attempt already retries the
        # database for about a minute (5 tries, delay doubling from 2 s), so
        # Airflow waits longer than that before trying again.
        "retries": 2,
        "retry_delay": pendulum.duration(minutes=2),
        "on_failure_callback": alert,
    },
    tags=["g04", "l07"],
) as dag:

    extracts = [
        container(
            f"extract_{table}",
            INGESTION_IMAGE,
            network_mode="albert-marketplace_default",
            environment={
                **GOOGLE_ENV,
                "DATABASE_URL": DATABASE_URL,
                "TABLE": table,
                # The interval this run covers. Full batch rereads the whole
                # table whatever the interval, so it is only logged.
                "RUN_INTERVAL": "{{ data_interval_start | ds }}",
            },
            mounts=[adc],
        )
        for table in TABLES
    ]

    recreate_live_tables = container(
        "recreate_live_tables",
        TRANSFORM_IMAGE,
        entrypoint="python",
        command=["-c", RECREATE],
        environment=GOOGLE_ENV,
        mounts=[adc, live_sql],
    )

    source_freshness = container(
        "source_freshness",
        TRANSFORM_IMAGE,
        command="source freshness",
        environment=GOOGLE_ENV,
        mounts=[adc],
    )

    dbt_build = container(
        "dbt_build",
        TRANSFORM_IMAGE,
        command="build",
        environment=GOOGLE_ENV,
        mounts=[adc],
    )

    extracts >> recreate_live_tables >> source_freshness >> dbt_build
