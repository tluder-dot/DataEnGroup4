# ADR-0007: Make every task safe to rerun by replacing what it writes, never appending

- **Status:** accepted
- **Date:** 2026-11-19
- **Author:** Jane Galthie
- **Lesson:** L07

## Context

The DAG reruns tasks on its own (2 retries), and a person reruns them after a
failure or for a back-fill. A task that appends would then double its rows,
and the revenue in gold with them. Each writing task needs a mechanism, named.

| Fact | Figure | Source |
|---|---|---|
| The extractor's mode | Full batch by default: every run rereads the whole table | ADR 0003 |
| Its size | 226,508 orders, 415,740 order lines; a full run of the DAG takes 2 min 38 s | 19 November, [docs/orchestration.md](../orchestration.md) |
| Where it writes | Fixed object names, `bronze/postgres/<table>/part-0.parquet`, `orders` one per year | `ingestion/extract_orders.py` |
| What dbt writes | Silver views and gold tables, no incremental model | `transform/dbt_project.yml` |
| A trusted unique key | `order_id` in PostgreSQL. Not `event_id` in the clickstream: it repeats after a restart of the load generator | #49 |
| Two reruns | Identical counts, bronze equal to the source | 19 November |
| Back-fill of 15 and 16 November | The same counts before and after, as predicted | 19 November |

## Options considered

| Option | For | Against |
|---|---|---|
| **Delete, then insert, by partition** | Only the interval is touched | Works when one interval is one partition. Breaks when a run spans partitions, or when the delete succeeds and the insert fails: the interval is gone |
| **MERGE on a business key** (the course's lab) | Updates and new rows in one statement; old rows stay | Needs a key we trust, and a test that it is unique. Misses deletes. Needs a staging table and a load step we do not have |
| **Write new, then swap** | The old version stays whole until the new one is complete; nothing accumulates | Rewrites everything at every run; storage doubles during the swap |
| **Accept duplicates** | Nothing to build | Never: the revenue would double at every rerun |

## Criteria

- **A rerun never changes the result**, whatever failed and when.
- **No partial state visible** to the next task.
- **Our size:** a full run takes 2 min 38 s, so rewriting everything costs little.
- **Few moving parts:** no staging table, no state to keep in step.

## Decision

**Every writing task writes new and swaps; none appends.**

| Task | Mechanism |
|---|---|
| `extract_<table>` | Write new, then swap: each file is rewritten under the same name, and Cloud Storage replaces an object whole |
| `recreate_live_tables` | Swap: `CREATE OR REPLACE EXTERNAL TABLE` |
| `dbt_build` | Swap: `CREATE OR REPLACE VIEW` in silver, one `CREATE OR REPLACE TABLE ... AS SELECT` per gold table |
| `source_freshness` | Writes nothing |

MERGE is rejected for now: full batch already sees updates and deletes (ADR
0003), and a run takes under three minutes. Delete-then-insert is rejected for
its window where the data is gone.

**The one I am least sure about: `extract_orders`.** It writes one file per
year. If it dies between two files, bronze holds some years from this run and
some from the last one, until a rerun rewrites them all. Each file is still
whole, and the rerun fixes it, but a run that reads bronze in between sees a
mix. The other extracts write a single file.

## Consequences

- **Easier:** any task, any day, can be rerun without thinking; the runbook
  says so. A back-fill is safe.
- **Harder:** **a rerun of a past day reloads today's database**, not that
  day's. Bronze keeps no history, so the shop on 15 November cannot be rebuilt.
  `RUN_INTERVAL` is passed to each extract but only logged.
- **Watch:** `airflow backfill create` ignores the DAG's `max_active_runs=1`:
  on 19 November two back-fill runs overlapped. Add `--max-active-runs 1`.
- **The clickstream is outside this decision.** Its consumer delivers at least
  once (ADR 0003), and silver removes the duplicates on (`event_id`,
  `emitted_at`).
- **What would change it:** a full run that no longer fits between two nights,
  or a need to see the past: then incremental extraction, MERGE on `order_id`,
  and bronze partitioned by run date.
