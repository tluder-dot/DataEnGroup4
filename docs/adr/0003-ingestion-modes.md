# ADR-0003: Read the database tables in full batch, and the clickstream as a stream, at least once

- **Status:** proposed
- **Date:** 2026-11-05
- **Author:** Jane Galthie
- **Lesson:** L03

## Context

Step 3 opens the live sources to bronze: seven tables of the PostgreSQL
database, and the clickstream on Kafka. The legacy export is already landed
([ADR-0002](0002-bronze-layout.md)). This ADR picks how each live source is
read, the delivery guarantee, and what would make us change.

| Fact | Figure | Source |
|---|---|---|
| Tables to carry | Seven: `orders`, `order_items`, `review`, `product_reviews`, `product`, `customer_shipping`, `shipping_details`. The biggest has 408,560 rows (`order_items`) | Brief, [data dictionary](../data-dictionary.md) |
| A date to use as a cursor | Only `orders` has one, `order_date`. `order_items` has none and needs a join | ADR-0002 |
| What a date cursor misses | A replication slot saw the `INSERT`, the `UPDATE` and the `DELETE` of a test product. A cursor on a date sees only new rows. The `DELETE` carries only the key, not the old values | CDC test, 5 November |
| An unread slot keeps log | 482 kB held while inactive, then dropped | CDC test, 5 November |
| Airbyte | Cannot reach our bucket or BigQuery: groups get no service account | Charles, 29 October |
| Duplicates after a crash | 200 after one crash between writing a file and committing its offset: one batch (`BATCH=200`). No event lost: 5,538 distinct events, all present | Crash test, 5 November |
| Malformed events | 4 sent, 4 in the dead letter queue, the consumer kept running | DLQ test, 5 November |
| Kafka retention | 168 hours, or 256 MiB in the topic | `albert-marketplace/compose.yaml` |
| `>` against `>=` on the cursor | **Pending T2** | Till's extractor |
| Duration of a full run | **Pending T2** | Till's extractor |

The tests and their commands are in
[docs/ingestion-failure-modes.md](../ingestion-failure-modes.md#evidence).

## Options considered

**Database tables**

| Option | For | Against |
|---|---|---|
| **Full batch:** reread each table at every run | Sees new rows, updates and deletes. A rerun gives the same snapshot. No state to keep | Reads every row at every run |
| **Incremental on `order_date`** | Reads only the new rows | Misses updates and deletes (CDC test). Only `orders` has the column. `>` misses rows sharing the last date, `>=` reads them twice |
| **CDC through Airbyte** | Sees all three changes, light on the database | Impossible here: no service account |
| **CDC with our own slot reader** | Sees all three changes without Airbyte | A slot nobody reads keeps log until the disk fills, and nothing keeps ours read before L07. A delete carries only the key |

**Clickstream**

| Option | For | Against |
|---|---|---|
| **Stream, at least once:** commit the offset after the file is written | No event lost. A crash duplicates at most one batch (200 measured) | Duplicates reach bronze. Silver deduplicates on `event_id` |
| **Stream, at most once:** commit before writing | No duplicates | A crash in the window loses the batch, without a trace |
| **Exactly once in bronze** | No duplicates, no loss | Cloud Storage has no transaction across a file and a Kafka offset. It needs a store of seen `event_id`s: more code for what silver does in one query |
| **Batch dump of the topic on a schedule** | One job instead of a running process | Same guarantee question, with older data. A missed run past 168 hours loses events |

## Criteria

- **Nothing lost in silence.** A duplicate can be found and removed; a
  missing row cannot. This rules out at most once and the date cursor as the
  default.
- **Sees what changes:** updates and deletes in the tables. Only full batch
  and CDC do; CDC is out of reach.
- **Rerunnable:** rerunning any interval gives the same result. Full batch
  does by construction.
- **Possible with our access:** personal logins, no service account, no
  scheduler before L07.
- **Effort at our size:** silver deduplicates in one query; an exactly once
  write would be a project of its own. The course plans the same split: the
  step 3 brief ends with "lesson 5 removes the duplicates".

## Decision

**Database tables: full batch by default.** The incremental cursor on
`order_date` stays as a second mode, because the brief asks for it, not as the
default. **Clickstream: streaming, at least once.** The offset is committed only
after the file is in the bucket, and silver deduplicates on `event_id`.

## Consequences

- **Easier:** after each run, the bronze tables match the source, deletes
  included, and a failed run is simply run again. No clickstream event is lost
  to a crash.
- **Harder:** every run rereads every table. Bronze holds clickstream
  duplicates, so anything that reads it before silver must deduplicate on
  `event_id`.
- **What would change this decision:**
  - **A full run taking longer than the interval between runs** (duration
    pending T2): move the big tables to the incremental mode, or to CDC.
  - **A service account, or the Airflow workaround the work plan announces:** reopens CDC
    through Airbyte, which sees updates and deletes without rereading.
  - **The consumer not running for 168 hours:** events are lost. If it cannot
    be run reliably at least once a week, the stream decision fails first.
  - **Deduplication in silver getting expensive:** lower `BATCH`, or write
    idempotently.
