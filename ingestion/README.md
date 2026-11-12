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

## The clickstream: `consume_clickstream.py`

Reads the topic `clickstream` and lands the events in
`bronze/clickstream/dt=YYYY-MM-DD/`, with the rejected ones in
`bronze/_dlq/clickstream/`. [clickstream_external.sql](clickstream_external.sql)
makes them readable as `g04_bronze_1.clickstream_external`.

### Run it as a service

The consumer runs as a container that Docker starts again after a crash or a
restart of Docker ([compose.yaml](compose.yaml), ADR 0003: a continuous
process, beside Airflow, not inside it). It needs the `albert-marketplace`
stack up, and your own Google login (`gcloud auth application-default login`).
From the repo root:

| To | Run |
|---|---|
| Start it | `docker compose -f ingestion/compose.yaml up -d` |
| See that it runs | `docker compose -f ingestion/compose.yaml ps` |
| Follow its log | `docker compose -f ingestion/compose.yaml logs -f` |
| See how far behind it is | `docker exec albert-marketplace-kafka-1 /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server kafka:9092 --describe --group clickstream-g04` (the `LAG` column) |
| Stop it | `docker compose -f ingestion/compose.yaml stop` |
| Move to a new image | Change the tag in `compose.yaml`, then `up -d` again |

**Stopping loses nothing.** The service resumes from the last offset it
committed, and unread events wait in Kafka for 168 hours.

**One reader only.** Never run `consume_clickstream.py` in a terminal with
`CONSUMER_GROUP=clickstream-g04` while the service runs. Two readers of one
group make Kafka share the partitions between them (a rebalance), and the
consumer then writes the events still in its buffer twice: 240 rows on
12 November. For a test, use another group, and `OUT` and `DLQ` in a local
folder.

**When your Google login expires,** writing to the bucket fails, the process
stops before committing, and Docker starts it again, over and over. Nothing
is lost, but nothing lands until you run
`gcloud auth application-default login` again. Read from the code, not tested.
