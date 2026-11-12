# ADR-0004: Keep BigQuery on demand, and cap every query

- **Status:** accepted
- **Date:** 2026-11-05 (accepted by Enzo on 2026-11-06)
- **Author:** Enzo Meret
- **Lesson:** L04

## Context

Step 4 puts the working set in native BigQuery tables
([warehouse tuning](../warehouse-tuning.md)). BigQuery has two ways to pay for
queries, and the choice sets what a careless query can cost.

**The workload, in numbers.** We have one measured day and everything else is
an estimate. Estimates are marked **(est.)**.

| Fact | Figure | Source |
|---|---|---|
| Data in the warehouse | 15 native tables, 232,719,290 bytes (0.217 GiB); 3 materialised views, 34,978,600 bytes | `g04_warehouse` table sizes, 5 Nov 2026 |
| The heaviest query we ran | 34,623,788 bytes: the collapse-ratio count over four joins | Our jobs, 5 Nov |
| The three project queries | 1.0 MB to 4.0 MB each when tuned (Q1 3,373,224; Q2 1,000,888; Q3 4,007,592) | [Warehouse tuning, section 3](../warehouse-tuning.md) |
| One working day of building and measuring, by one person | 108 SELECT jobs, 925,676,327 bytes processed = **0.00084 TiB** | `INFORMATION_SCHEMA.JOBS_BY_USER`, `region-europe-west1`, last 24 h, 5 Nov |
| Free tier | First 1 TiB per month | Course lecture 4; [cloud.google.com/bigquery/pricing](https://cloud.google.com/bigquery/pricing), read 5 Nov |
| On demand | $7.50 per TiB processed, in `europe-west1` | Course lecture 4, read 24 Sep 2026 |
| Billing minimum | 10 MiB per query and per table referenced | Same page |
| Capacity (Standard edition) | $0.04 per slot-hour pay as you go, billed per second with a 1-minute minimum | Same page, 5 Nov. **We could not tie this figure to `europe-west1`**: the page lists one row for many regions. The on-demand price for the US regions on that page ($6.25) is lower than the course's $7.50 for Europe, so the Europe slot price may be higher too |
| Concurrent users | The 4 of us now. ML team and analysts later: **(est.)** 5 to 10 | Work plan; estimate |
| Queries per day | **(est.)** 50 to 500 once dbt runs and dashboards exist | Estimate. We have no production usage |
| Concentration in time | **(est.)** a daily dbt run plus office hours | Estimate |
| Who sees the bill | The cohort shares one project and its budget | Course; `CLAUDE.md` |

**Constraint.** We cannot read the project-wide job history:
`INFORMATION_SCHEMA.JOBS_BY_PROJECT` is refused (403, `bigquery.jobs.listAll`).
Our own usage is the only usage we can count.

## Options considered

| Option | For | Against |
|---|---|---|
| **On demand, with a `maximum_bytes_billed` cap on every query** | No idle cost. Our measured usage is about 40× under the free tier (see below). Nothing to size or switch off | One careless query has no ceiling unless we set the cap. The cap must be set on each query or in each tool |
| **Capacity, Standard edition, pay as you go** | A fixed price per hour of compute, not per byte. A cap on spend that holds for any query | The smallest billed burst is 50 slots (**(est.)**, from the page's 50-slot unit) for one minute: 50 × $0.04 ÷ 60 = **$0.033**, against $0.00024 for our heaviest query on demand (**140×**). Idle time costs if the autoscaler holds slots. Needs a reservation and an assignment, which need permissions we may not have in a shared project |
| **Capacity with a commitment (Enterprise, 1 or 3 years)** | Cheaper per slot-hour at steady load ($0.054 and $0.048 for 1 and 3 years on the page, region not confirmed) | A year of payment for a workload that fits in the free tier. Not available on Standard |
| **A different warehouse (Snowflake, Databricks SQL)** | Per-second billing with auto-suspend | The platform, the external tables and the dbt adapter in L05 are BigQuery. Not argued here |

## Criteria

- **Cost at our size and at 1,000× the data.**
- **Worst case from one careless query.**
- **Effort and permissions.** We cannot create service accounts or read
  project-wide jobs.
- **Whether the features we built pay under the meter.** The materialised view
  saved 1.12 to 1.14× the bytes at the star's grain: little under a byte meter,
  but a saving of aggregation work under a time meter.

The crossover arithmetic. On demand costs (TiB − 1) × $7.50 per month.
Capacity costs 50 slots × $0.04 × the hours it runs. They are equal at
**TiB = 1 + 0.2667 × hours** (50 slots × $0.04 ÷ $7.50 = 0.2667):

| Capacity runs | Capacity cost per month | On demand is cheaper below |
|---|---|---|
| 1 hour per month | $2.00 | 1.27 TiB per month |
| 1 hour per day (30 h) | $60 | **9.0 TiB** per month |
| 8 hours per day (240 h) | $480 | 65 TiB per month |
| 24 hours per day (720 h) | $1,440 | **193 TiB** per month |

| Scenario | TiB per month | On demand | Verdict |
|---|---|---|---|
| Today, one person, an intense day repeated 30 times | 0.025 | **$0** (free tier) | On demand |
| 10 people, each at today's pace for 30 days | 0.25 **(est.)** | **$0** | On demand |
| Same, and **1,000× the data** | 250 **(est.)** | $1,867 | The 24-hour line (193 TiB) is crossed: capacity may win, and so does shrinking the scans |
| One query that scans the whole dataset (0.25 GiB today), at 1,000× the data | 0.24 TiB per query **(est.)** | $1.83 per query | A cap of 100 MiB would have refused it |

(0.00084 TiB × 30 = 0.025. 250 TiB: (250 − 1) × $7.50 = $1,867.50.)

**What we could not find out:** the real concurrency and the number of queries
once dashboards exist; the Europe price per slot-hour; whether our project is
allowed to create a reservation at all. The cohort's free tier is counted
"per account", which we read as one account for the whole project: other groups
may use it up first. We could not check.

## Decision

*Proposed:* **stay on demand, and put a `maximum_bytes_billed` of 100 MiB on every
query we script and every exploratory query in the console.** One person's
heavy day, repeated for 30 days, is 0.025 TiB; the free tier is 1 TiB, so we
are **40× under it** (1 ÷ 0.025). Capacity would add a fixed floor cost for
no gain.

## Consequences

- **Easier:** no reservation to size, no idle cost, no permission to ask for.
  Q1 to Q3 cost under $0.0001 each.
- **Harder:** nothing stops a query that has no cap. The cap is a habit and a
  setting in [`warehouse/measure.py`](../../warehouse/measure.py), not a
  project-level rule. A project default or `require_partition_filter` on the
  silver fact table (L05) would turn the habit into a rule.
- **The cost of the decision, in the worst case:** unbounded bill from one
  careless query. A 100 MiB cap bounds each *capped* query at
  104,857,600 ÷ 2^40 × $7.50 = **$0.0007.** An uncapped query that scans
  the whole dataset at 1,000× would cost about $1.83. We accept that for queries
  nobody capped.
- **The materialised view** does not pay under this meter at the star's grain
  (1.12 to 1.14×). It would free slots under capacity pricing. If we move to
  capacity, revisit it ([warehouse tuning, section 4](../warehouse-tuning.md)).
- **What would change my mind, as a number someone can watch:**
  - **Our monthly bytes processed** (`SUM(total_bytes_processed)` from
    `INFORMATION_SCHEMA.JOBS_BY_USER`, per month, per person) **above 0.5 TiB.**
    Half the free tier leaves room for a month we cannot see.
  - **Or a single month above 9 TiB:** the crossover with one hour of capacity
    per day (**TiB = 1 + 0.2667 × 30**).
  - **Or one query above 1 GiB** ($0.0073): the cap would be too tight, or the
    table has lost its partition filter. The
    [slow-query runbook](../runbooks/slow-query.md) starts there.
