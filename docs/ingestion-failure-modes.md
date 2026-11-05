# Ingestion failure modes

What can go wrong on each path into bronze, whether we handle it, and what
happens if it occurs. State on 5 November 2026. Every figure says where it
comes from; the commands are under [Evidence](#evidence).

Three paths are planned (ADR 0003). On 5 November, two exist: the export and
the clickstream consumer. The extractor for the database tables (T2) is not on
`main` yet, so its rows say **pending T2** and describe the plan in
[docs/workplan.md](workplan.md), not a measurement.

## Where the credentials live

- **Google Cloud:** each member's personal login, `gcloud auth login` and
  `gcloud auth application-default login`. No service account: groups get none
  in this project (Charles, 29 October). The consumer writes with the
  application default credentials, through `gcsfs`.
- **PostgreSQL:** `DATABASE_URL` in each member's local `.env`, copied from
  `.env.example` and never committed (`.gitignore`).
- **Kafka:** none. The local broker has no authentication (`PLAINTEXT` in
  `albert-marketplace/compose.yaml`).

So every pipeline runs as the person who starts it, from their own machine.
When that person's login lapses, the pipeline stops.

**Who can read them.** The Google tokens sit in each member's home folder
(`~/.config/gcloud/`), and `DATABASE_URL` in their `.env`: readable by that
member's account on their own machine, and by no one else. Nothing is in the
repo: `.gitignore` blocks `.env` and key files. No long-lived key exists, no
service account key and no HMAC key, so nothing outlives a member's login.

**How to revoke them.** On the member's machine, `gcloud auth revoke` removes
the `gcloud` login and `gcloud auth application-default revoke` removes the
credentials the consumer writes with.

## Clickstream: topic `clickstream` → `bronze/clickstream/`

[`ingestion/consume_clickstream.py`](../ingestion/consume_clickstream.py),
validated against
[`ingestion/clickstream.schema.json`](../ingestion/clickstream.schema.json).
At least once: each file is written before its Kafka offset is committed.

| Failure | Handled? | By what | What happens if it occurs |
|---|---|---|---|
| New events | Yes | The consumer reads every message after the offset its group committed | They land in `bronze/clickstream/dt=<date of event_time>/` |
| Updates | Not handled | | An event is a fact and is never corrected. The site sends no correction or cancellation event, so a cancelled order still shows as `order_placed`. The state of an order comes from the `orders` table, not from the clickstream |
| Deletes | Not handled | | No event deletes anything, and bronze never deletes: [the lifecycle rules](../infra/lifecycle.json) only move files to colder classes. Erasing one buyer's events on request (GDPR) would mean rewriting every file that holds their `buyer_id`. We have no tool for it |
| Kafka down | Partly, not tested | The client library retries the connection; the loop prints `kafka error` and keeps polling | Nothing is read or written while it is down. Nothing is lost on our side, because the committed offset does not move. Not tested |
| Consumer stopped, restarted within retention | Yes | The offset committed in the consumer group | It resumes at the first message it had not committed |
| Consumer stopped longer than retention | **Not handled** | | Kafka deletes messages after 168 hours, or earlier once the topic passes 256 MiB. Unread messages older than that are lost for good, and no one is warned. Nothing starts the consumer on a schedule yet (L07) |
| Malformed event | Yes | JSON parsing, then the schema, before an event is accepted | The message goes to `bronze/_dlq/clickstream/` with the raw message, the reason, the time, the topic, the partition and the offset. The flow continues. Tested: 4 broken messages, all 4 in the DLQ, the consumer kept writing |
| Impossible date | Yes | A date parse after the schema | `2026-13-45T00:00:00Z` has the right shape but no such day. It goes to the DLQ (`month must be in 1..12`) instead of crashing the whole batch |
| Schema change: new field | Partly | The schema accepts unknown fields | Events keep landing, with the new column. Nobody is alerted, and only files written after the change have it |
| Schema change: missing or renamed field, wrong type | Yes | The schema | Every such event goes to the DLQ with its reason. Bronze misses them until the schema is updated and the DLQ replayed |
| Schema change: new `schema_version` | Yes | The consumer picks the schema by `schema_version` | An unknown version goes to the DLQ (`unknown schema_version: 2`, tested). Accepting it takes a new schema file and one line in `SCHEMAS` |
| Replaying the DLQ | **Not handled** | | Each row keeps the topic, partition and offset to find the message again, but no tool replays it |
| Duplicate after restart | Yes, by design | At least once | A crash between writing a file and committing its offset writes that batch again. Measured: 200 duplicates after one crash, exactly one batch (`BATCH=200`). Silver must deduplicate on `event_id` |
| Expiring credential | **Not handled** | | If the application default credentials can no longer refresh, the write in `flush()` raises and the process stops before committing. After the person logs back in, the batch is read again: no loss, possible duplicates. Read from the code, not tested. The `gcloud` login did lapse on 5 November and asked for a password |
| Write refused on the bucket | **Not handled** | | Same as an expired credential: the process stops before committing |
| Small files | **Not handled** | | Once caught up, the consumer writes whenever the topic is quiet for a second. Seen on 5 November: files of 1 to 11 rows. Many small files slow every later read |
| Nobody watching | **Not handled** | | No alert when the DLQ fills, the consumer stops or a login lapses |

## Database tables: PostgreSQL → bronze

Two paths. **The export**,
[`ingestion/land_export.py`](../ingestion/land_export.py), landed the 27
tables of the v1.0.0 CSV export once; it never reads the database. **The
extractor**, `ingestion/extract_orders.py` (T2, Till), will read seven tables
from the live database, full batch by default and incremental on `order_date`
as a second mode. It is not on `main` on 5 November.

| Failure | Handled? | By what | What happens if it occurs |
|---|---|---|---|
| New rows | Pending T2 | Full batch rereads the table; incremental reads the rows past the cursor | Today, new rows in the database do not reach bronze at all: the export is a snapshot |
| Updates | Pending T2 | Full batch only | Full batch sees them at the next run. A cursor on `order_date` does not, because an update keeps the row's date. CDC test: a replication slot saw an `UPDATE` that a date cursor would miss |
| Deletes | Pending T2 | Full batch only | Full batch sees a deleted row as missing from the new snapshot. An incremental cursor never sees it. The CDC test saw the `DELETE`, carrying only the key, not the old values |
| Source down | Pending T2 | Planned: retries with a growing delay, then a clean failure | Nothing lands until the database is back |
| Malformed row | Pending T2 | The database's own types and keys | A row cannot be malformed the way a message can. The export's deliberate defects (index column, leading zeros, NA-like strings) land as they are and are fixed once in silver |
| Schema change | Pending T2 | Columns selected by name | A new column is ignored until it is added to the query. A dropped or renamed column makes the query fail |
| Duplicate after restart | Pending T2 | | Full batch rereads the whole table, so a rerun gives the same snapshot. For incremental, `>` or `>=` on the cursor decides between missing rows and duplicating them; T2 records which |
| Expiring credential | **Not handled** | | `DATABASE_URL` does not expire, but the Google login that writes to the bucket does, and the run stops |

## Evidence

All on 5 November 2026, by Jane, on the local `albert-marketplace` stack.

| What | How | Result |
|---|---|---|
| Duplicates after a crash | `CONSUMER_GROUP=clickstream-jg-crash`, `OUT` and `DLQ` in a local folder, `BATCH=200`, `PAUSE_BEFORE_COMMIT=20`; killed during the first pause, restarted with the same group, then rows and distinct `event_id` counted with pandas | 36 files, 5,738 rows, 5,538 distinct, **200 duplicates** (15:41 UTC) |
| Dead letter queue | 4 broken messages sent with `kafka-console-producer.sh` while `clickstream-g04` ran | 4 rows in `bronze/_dlq/clickstream/dt=2026-11-05/`, offsets 1556 to 1559; the consumer kept writing (15:06 UTC) |
| What a date cursor misses | Slot `pg_create_logical_replication_slot('cdc_jg', 'test_decoding')`; insert, update and delete of test product `EX1JG`; `pg_logical_slot_peek_changes` | 3 changes seen. The slot held 482 kB of log, inactive, then was dropped; 0 slots left (15:43 UTC) |
| Kafka retention | `KAFKA_LOG_RETENTION_HOURS` and `KAFKA_LOG_RETENTION_BYTES` in `albert-marketplace/compose.yaml` | 168 hours, 268,435,456 bytes (256 MiB) |
