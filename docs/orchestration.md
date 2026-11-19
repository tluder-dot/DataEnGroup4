# Orchestration

How the pipeline runs on a schedule, and the evidence that each part behaves.
Step 7, L07. State on 19 November 2026; every figure gives its run and time
(UTC), and the raw outputs are kept by Jane.

## What runs

[`orchestration/dags/marketplace_g04.py`](../orchestration/dags/marketplace_g04.py),
DAG `g04_marketplace_daily`, every day at 02:00 UTC, covering the day before.

```
extract_<table> (x7) >> recreate_live_tables >> source_freshness >> dbt_build
```

| Task | Image | Does |
|---|---|---|
| `extract_<table>`, one per table | `group4-ingestion` | Reads the whole table from PostgreSQL, writes `bronze/postgres/<table>/` |
| `recreate_live_tables` | `group4-transform` (its BigQuery client) | Runs [`ingestion/extract_external_tables.sql`](../ingestion/extract_external_tables.sql): the seven `<table>_live` tables, so dbt's freshness sees the new load |
| `source_freshness` | `group4-transform` | `dbt source freshness`: red when a source is past its error threshold |
| `dbt_build` | `group4-transform` | Models and tests together: the quality gate |

Every task is a container from our images, tag `20261118-796cf3e`
([ADR 0006](adr/0006-image-registry-and-tags.md)): the DAG holds no query and
no pandas. The run's period reaches each extract as
`RUN_INTERVAL={{ data_interval_start | ds }}`, never the clock. Full batch
rereads the whole table whatever the period, so it is only logged
([ADR 0007](adr/0007-idempotency.md)).

**The clickstream is not a task.** Its consumer is a service of its own
([`ingestion/compose.yaml`](../ingestion/compose.yaml), ADR 0003). The DAG only
checks that its data is fresh.

## Run it

Airflow 3.3.2, from the course's L07 lab, lives in `orchestration/`. Copy
[`orchestration/.env.example`](../orchestration/.env.example) to
`orchestration/.env` (never committed) and fill in your paths and the Discord
webhook. Then, with the `albert-marketplace` stack up:

```
cd orchestration
docker compose build && docker compose up airflow-init
docker compose up -d postgres redis airflow-apiserver airflow-scheduler airflow-dag-processor airflow-worker
```

The triggerer is left out on purpose: no task here defers, and it costs about
500 MB. The UI is at http://localhost:8080.

## Resources

Measured on Jane's MacBook Air (8 GB, Docker limited to 5 GB).

| What | Figure | When |
|---|---|---|
| Airflow, idle, 7 services | 1.50 GB | 6 November |
| The shop stack and the consumer | 0.73 GB | 6 November |
| Free memory of the Mac during the green run | 32 % at the lowest | 19 November |

**Two tasks at a time did not fit.** On 18 November, with two extracts at once,
Langfuse still running and the usual apps open, the Mac ran out of memory:
Kafka, the Airflow worker and the triggerer were killed (`Exited (137)`), and
Kafka stayed down for about 18 hours without anyone being told. The DAG now
runs one task at a time (`max_active_tasks=1`) and the triggerer is stopped.

## The green run

Run `scheduled__2026-11-19T02:00:00+00:00`, 19 November, 12:30:12 to 12:32:50:
**2 min 38 s**, ten tasks, all `success`.

| Step | Time |
|---|---|
| Seven extracts, one at a time | 1 min 10 s (4 to 15 s each) |
| `recreate_live_tables` | 8 s |
| `source_freshness` | 12 s |
| `dbt_build` | 53 s |

## Idempotency

| Task | What it writes | Why running it twice is safe |
|---|---|---|
| `extract_<table>` | `bronze/postgres/<table>/part-0.parquet`; `orders` one file per `order_year` | Full batch: it rewrites the same object names, and a Cloud Storage object is replaced whole, never appended to. Rerun, it writes the same files with today's rows |
| `recreate_live_tables` | Seven external tables, metadata only | `CREATE OR REPLACE`: the definition is replaced, nothing accumulates |
| `source_freshness` | Nothing outside its container | Reads only |
| `dbt_build` | Silver views, gold tables | Views: `CREATE OR REPLACE VIEW`. Gold tables: dbt's table materialisation is one `CREATE OR REPLACE TABLE ... AS SELECT`, so the new table replaces the old one in one statement |

**Measured.** The load generator was stopped, so the source could not move.
The run of 19 November was cleared and run twice, and counted after each:

| | Rerun 1, 12:44:44 to 12:47:13 | Rerun 2, 12:47:26 to 12:50:37 |
|---|---|---|
| `orders` in PostgreSQL | 226,458 | 226,458 |
| `orders_live` in bronze | 226,458 | 226,458 |
| `order_items`, PostgreSQL and bronze | 415,626 and 415,626 | 415,626 and 415,626 |
| Files under `bronze/postgres/orders/` | 4 | 4 |
| Lines in `g04_gold.fct_order_items` | 211,342 | 211,342 |
| Revenue in gold | 20,253,973.11 | 20,253,973.11 |

Identical, and bronze equals the source. **A first attempt was not identical**:
the generator was stopped after the first run instead of before it, so 9
orders placed in between reached the rerun (+9 orders, +22 lines). Had the
rerun appended, bronze would have doubled, about 226,000 more orders.

## Retries and the alert

Every task: **2 retries, 2 minutes apart**, so three attempts. Each extract
already retries the database 5 times, the delay doubling from 2 s (about a
minute in all), so Airflow waits longer than what it retries.

After the last attempt, `on_failure_callback` prints the alert into the task's
log and posts it to the Discord channel `#pipeline-alerts`:

```
ALERT g04_marketplace_daily.extract_orders failed for 2026-11-18 after 3 tries. Runbook: docs/runbooks/failed-run.md
```

**Who sees it:** Jane, on her phone (the DAG runs on her laptop). **What she
does:** [docs/runbooks/failed-run.md](runbooks/failed-run.md). The webhook URL
is a secret: only in `orchestration/.env`.

It fired for real on 18 November at 18:57: all seven extracts failed on a
credentials problem (the runbook's first breakage), and seven alerts arrived.

## The quality gate

`dbt_build` runs the models and their tests together: a test that fails skips
everything built on that model, so the bad number never reaches gold.

**The drill, 19 November.** The test chosen: `not_null` on
`stg_orders.buyer_id`, which is an error, not a warning. The database lets it
through: a deleted buyer sets `orders.buyer_id` to NULL (`ON DELETE SET NULL`).
Quantities of 0 and ratings of 7 could not be used: the database refuses them.

| Step | Result |
|---|---|
| Poison row | `INSERT INTO orders (buyer_id, order_date) VALUES (NULL, CURRENT_DATE)`: order 226557 |
| The run | `failed`, 12:53:51 to 13:00:33: `dbt_build` failed three times |
| The test | `FAIL 1 not_null_stg_orders_buyer_id` |
| What was skipped | `int_orders`, `int_order_items`, `dim_date`, `assert_no_twin_orders` and everything after |
| Did the alert arrive | **Yes**: the `dbt_build` alert reached `#pipeline-alerts` on Discord. |
| Gold before | 211,342 lines, 20,253,973.11; `fct_order_items` last modified 12:50:26, `fct_daily_demand` 12:50:31 |
| Gold after | **The same**: 211,342 lines, 20,253,973.11, same last-modified times |
| Clean-up | `DELETE FROM orders WHERE order_id = 226557`; the run cleared and green again, 13:15:56 to 13:18:03 |

## The back-fill

**Range asked:** 15 to 17 November, three days that had never run. The load
generator was stopped.

**Prediction, written before:** full batch ignores the run's date, so each run
reloads today's database, and the counts after equal the counts before.

**Dry run:** `airflow backfill create --dag-id g04_marketplace_daily
--from-date 2026-11-15 --to-date 2026-11-17 --dry-run` listed **two** runs, 15
and 16. A daily run at 02:00 on the 17th falls after `--to-date 2026-11-17`,
which means midnight.

| | Before, 13:18:33 | After, 14:51:44 |
|---|---|---|
| `orders`, PostgreSQL and bronze | 226,508 and 226,508 | 226,508 and 226,508 |
| `order_items`, PostgreSQL and bronze | 415,740 and 415,740 | 415,740 and 415,740 |
| Files under `bronze/postgres/orders/` | 4 | 4 |
| Lines in gold | 211,446 | 211,446 |
| Revenue in gold | 20,261,896.25 | 20,261,896.25 |

Runs `backfill__2026-11-15` (13:18:43 to 13:23:46) and `backfill__2026-11-16`
(13:18:43 to 13:20:55): both `success`. **As predicted.**

**Why the actual differs from what was asked:** two runs, not three (the date
boundary above). And **the two runs overlapped**, both starting at 13:18:43:
`airflow backfill create` does not apply the DAG's `max_active_runs=1`. Here it
broke nothing, since the source was frozen and both runs wrote the same files.
Next time: add `--max-active-runs 1`.

## Limits

- **A rerun of a past day loads today's database**, not that day's: full batch
  keeps no history. Bronze cannot rebuild what the shop looked like on the 15th.
- **The pipeline runs on Jane's laptop.** Asleep or off at 02:00, the run is
  skipped (`catchup=False`): the next one covers it, since it rereads everything.
- **Nothing watches Kafka.** On 18 November it was killed and stayed down for
  about 18 hours; only the clickstream's freshness check could have seen it,
  after one day.
