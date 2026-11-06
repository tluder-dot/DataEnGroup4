# Ingestion

Arrives in **L03 · Batch, streaming, CDC**: the pipelines that bring Albert's
Marketplace's data into the bronze layer.

In **L06** each ingestion job gets its Dockerfile here.

## The legacy export: `land_export.py`

Lands the 27 CSV files in `gs://data-engineering-i1-g04/bronze/<table>/` as
Parquet, and creates the external tables `g04_bronze_1.<table>_external`.
`customer.pwd`, `payment_details.card_no` and `cvv` are never read.

The dataset was created once, with:

```
bq --location=europe-west1 mk --dataset --label=group:g04 --label=layer:bronze data-engineering-i1:g04_bronze_1
```

To rerun the landing (pandas and pyarrow, and your own `gcloud` login):

```
python ingestion/land_export.py --src <folder of the CSV files> --upload --external
```

If `gcloud storage rsync` stops with `gcloud-crc32c: command not found`, run
`gcloud components install gcloud-crc32c` once.

## The database tables: `extract_orders.py`

Reads seven tables from PostgreSQL with plain SQL and writes Parquet under
`gs://data-engineering-i1-g04/bronze/postgres/`, with your own Google login
(`gcloud auth application-default login`). `DATABASE_URL` comes from your
`.env`.

| Mode | Set | Writes |
|---|---|---|
| Full batch, the default | `TABLE=<table>` | `bronze/postgres/<table>/`, replaced at each run |
| Incremental, `orders` only | `MODE=incremental` | `bronze/postgres/_incremental/orders/`, one file per run, with the cursor in `bronze/postgres/_state/orders.json` |

All seven tables:

```
set -a; source .env; set +a
for t in orders order_items review product_reviews product customer_shipping shipping_details
do TABLE=$t python ingestion/extract_orders.py; done
```

For a local test, set `OUT` to a folder. `CURSOR_OP`, `RETRIES` and
`RETRY_DELAY` are settings too.
