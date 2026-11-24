#!/usr/bin/env python3
"""Put the salt of pseudonymise() into pii_salt, by default in g04_secrets.

Run it once, with the salt in the environment (never on the command line):

    PII_SALT=<64 random hex characters> python transform/seed_pii_salt.py

--dataset chooses where the salt goes (default g04_secrets): a test run writes a
throwaway salt into a dataset of its own.

It uses a load job, so the salt travels as data: no SQL text holds it, and the
job history cannot show it. It refuses to replace a salt that exists, because a
new salt gives every person a new hash. Use --rotate to replace it on purpose.
Needs the dataset g04_secrets to exist already.
"""
import argparse
import io
import os
import sys

from google.cloud import bigquery

PROJECT = "data-engineering-i1"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rotate", action="store_true", help="replace an existing salt")
    parser.add_argument("--dataset", default="g04_secrets", help="where the salt goes")
    args = parser.parse_args()
    table = f"{PROJECT}.{args.dataset}.pii_salt"

    salt = os.environ.get("PII_SALT", "")
    if len(salt) < 32:
        sys.exit("PII_SALT is missing or shorter than 32 characters; nothing written")

    client = bigquery.Client(project=PROJECT, location="europe-west1")
    try:
        client.get_table(table)
        exists = True
    except Exception:
        exists = False
    if exists and not args.rotate:
        sys.exit(f"{table} already holds a salt; use --rotate to replace it")

    job = client.load_table_from_file(
        io.BytesIO((salt + "\n").encode()),
        table,
        job_config=bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            schema=[bigquery.SchemaField("salt", "STRING", mode="REQUIRED")],
            write_disposition="WRITE_TRUNCATE",
            labels={"group": "g04"},
        ),
    )
    job.result()
    print(f"wrote the salt ({len(salt)} characters) to {table}, job {job.job_id}")


if __name__ == "__main__":
    main()
