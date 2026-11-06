# ADR-0005: Build silver as views and gold as tables

- **Status:** accepted
- **Date:** 2026-11-06
- **Author:** Till Lüder
- **Lesson:** L05

## Context

dbt turns each model into a view, a table or an incremental table. That choice
sets who pays for a query, and how fresh the answer is. The project has 13
silver models and 5 gold models ([transform/](../../transform/README.md)), read
by analysts and the ML team once a day.

| Fact | Figure | Source |
|---|---|---|
| Same question on gold and on silver: units per country, last quarter | Table: 119 ms, 33 slot-ms. Through the views: 5,526 ms, 13,103 slot-ms. 46× slower, about 400× the compute | `JOBS_BY_USER`, 3 runs each, cache off, 6 November |
| A gold build | Reads 114 MiB. The whole project, tests included, takes 43 s | `dbt build`, 6 November |
| Built every night | 3.3 GiB a month: 0.3 % of the free 1 TiB, about $0.02 at $7.50 per TiB | Arithmetic on the above |
| Gold's storage | 42 MB, about $0.0008 a month | `__TABLES__`, 6 November |
| Late rows | A twin lands up to 4 days after its original | Data dictionary, trap 6 |

## Options considered

| Option | For | Against |
|---|---|---|
| **Everything views** | Always fresh, nothing stored, nothing to run | Every consumer pays the full chain at every read: 5.5 s instead of 0.1 s |
| **Everything tables** | Fast everywhere | Silver is stored twice and goes stale between runs, and it has no direct consumer to justify that |
| **Views, then tables** | Silver is fresh and stored nowhere. Gold reads fast | Gold is only as fresh as the last run. A build is one more step to schedule |
| **Incremental gold** | Cheapest rebuilds | We must define "new". `fct_daily_demand` would need to reopen 4 days at each run, or a twin's rule could go wrong in silence. It saves about $0.02 a month |

## Criteria

- **Who pays:** consumers read every day, the build runs once.
- **Cost at our size:** 0.3 % of the free tier, so cheap rebuilds buy nothing.
- **Risk of silent error:** incremental is the one that can be wrong for months
  with every test green.
- **Freshness:** a daily refresh is enough for both consumers (ADR-0001).

## Decision

Silver (`staging/`, `intermediate/`) is views, in `g04_silver`. Gold (`marts/`)
is tables rebuilt in full at each run, in `g04_gold`. `fct_order_items` and
`fct_daily_demand` are partitioned by month and clustered, the shape
[warehouse tuning](../warehouse-tuning.md) measured.

## Consequences

- **Easier:** a change to a rule reaches gold at the next build, with no
  backfill. Reads are fast and cheap.
- **Harder:** gold is as old as the last run, so it needs the nightly schedule
  of step 7. Silver reads Parquet at every query, so debugging on it is slower.
- **What would change this decision:**
  - **A full build taking an hour,** or the monthly bytes nearing the free
    1 TiB, about 300 times today's: move the facts to incremental, and define
    "new" with a 4-day window.
  - **A consumer needing minute-fresh data:** gold as views for that table.
  - **A consumer reading silver directly:** that model becomes a table.
