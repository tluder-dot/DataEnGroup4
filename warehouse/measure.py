"""Measure a BigQuery query the way docs/warehouse-tuning.md reports it.

Prints the dry-run estimate, then runs the query with the query cache OFF and
prints bytes processed (never bytes billed: billing has a 10 MiB minimum per
table). The two numbers should match.

Usage:
    python warehouse/measure.py "SELECT ..." [maximum_bytes_billed]

The cap defaults to 100 MiB; a query above it fails without charge.

Credentials: your own login (`gcloud auth application-default login`), no key
file. Needs `pip install google-cloud-bigquery`.
"""

import sys

from google.cloud import bigquery

PROJECT = "data-engineering-i1"
LOCATION = "europe-west1"
DEFAULT_CAP = 100 * 2**20  # 100 MiB: see docs/warehouse-tuning.md, section 5
PRICE_PER_TIB = 7.50  # USD, on demand, europe-west1: the course's lecture 4 (read 2026-09-24)


def measure(sql: str, maximum_bytes_billed: int = DEFAULT_CAP) -> None:
    client = bigquery.Client(project=PROJECT, location=LOCATION)

    dry = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True))
    print(f"dry run:         {dry.total_bytes_processed:>12,} bytes")

    config = bigquery.QueryJobConfig(
        use_query_cache=False, maximum_bytes_billed=maximum_bytes_billed
    )
    job = client.query(sql, job_config=config)
    rows = list(job.result())

    cost = job.total_bytes_processed / 2**40 * PRICE_PER_TIB
    print(f"bytes processed: {job.total_bytes_processed:>12,}")
    print(f"cache hit:       {job.cache_hit}")
    print(f"rows returned:   {len(rows):>12,}")
    print(f"cost at ${PRICE_PER_TIB}/TiB: ${cost:.7f}")


if __name__ == "__main__":
    measure(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_CAP)
