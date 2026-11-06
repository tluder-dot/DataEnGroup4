# Runbook: a query that took 2 seconds now takes 2 minutes

For whoever is on call at 23:00. You do not need to understand the platform.
Follow the steps in order: each one is cheaper and likelier than the next, and
says what it rules in or out.

**Where:** BigQuery console, project `data-engineering-i1`, dataset
`g04_warehouse`, location `europe-west1`. Every query you run now costs money:
**set *Maximum bytes billed* to 104857600 first** (*More → Query settings →
Advanced options*).

**Stop and escalate** when any of these is true (see the end of this page):
you have done all six steps, or a single query has processed more than 1 GiB,
or the data looks wrong rather than slow.

## Before step 1: get two numbers

Open the slow query in *Job history* (bottom of the console, *Personal history*
or *Project history*; you may see only your own jobs). Click the job, then the
**Job information** tab. Write down:

- **Bytes processed** (not *bytes billed*: billing rounds up to 10 MiB per
  table and hides the change).
- **Duration** and **Slot milliseconds consumed**.

Do the same for a run of the same query from when it was fast, if you have it
(Job history, an older run). Then go through the steps.

## Step 1 · Is the "fast" one a cache hit? (30 seconds)

**Why first:** it costs nothing and it is the most common false alarm.

**Where:** the fast run's *Job information* tab, the line **Bytes processed**.
Or *Query settings* on the slow run: is *Use cached results* ticked?

**Gives it away:** the fast run says **0 B processed** or *Cache hit: yes*. On
5 November 2026 the same query processed 1,000,888 bytes the first time and
0 the second.

**What to do:** untick *Use cached results* (*More → Query settings*) and
rerun. If the slow run is now the normal run, **nothing is wrong.** Stop. Write
down that the earlier time was a cache.

## Step 2 · Did the query lose its partition filter? (2 minutes)

**Why second:** a change to the SQL is the most likely real cause, and it
costs nothing to check.

**Where:** click **Dry run**, or the validator tick at the top right of the
editor: it prints *"This query will process N bytes"*. Compare N with the
**Bytes processed** you wrote down for the fast run.

**Gives it away:** bytes processed **jumped**, and the `WHERE` no longer
compares the partition column (`order_date`) with a constant. On
`order_items_month_pc`, selecting `p_id` and `qty`:

| `WHERE` on `order_date` | Bytes |
|---|---|
| `>= DATE '2026-06-15' AND <= DATE '2026-09-14'` | 1,000,888 |
| none | 3,302,820 |
| `FORMAT_DATE('%Y-%m', order_date) >= '2026-06'` (wraps the column) | 9,995,468 |
| `IN (SELECT ...)` | 11,439,680 |
| dates come from a `JOIN` | 15,001,984 |

The last three are worse than no filter at all: they read `order_date` as well.

**What to do:** rewrite the filter so that `order_date` is compared to a
constant (`>= DATE '...'`). If the bytes come back to the old value, that was
it. If the bytes did not change, go on.

## Step 3 · Did the table outgrow its grain? (3 minutes)

**Why third:** the SQL is unchanged and the bytes grew slowly. It takes
longer to check and longer to fix than the first two.

**Where:** run, with the cap still set:

```sql
SELECT table_name, COUNT(*) AS partitions,
       CAST(ROUND(AVG(total_logical_bytes)) AS INT64) AS avg_bytes
FROM `data-engineering-i1.g04_warehouse.INFORMATION_SCHEMA.PARTITIONS`
WHERE table_name LIKE 'order_items_%' OR table_name LIKE 'orders_%'
GROUP BY table_name ORDER BY partitions DESC;
```

**Gives it away:** compare with 5 November 2026:

| Table | Partitions | Average partition |
|---|---|---|
| `order_items_month_pc` | 37 | 485,855 bytes |
| `orders_month` | 37 | 421,238 |
| `order_items_day` | 1,096 | 16,402 |

The partition count or the average size has **moved**. A monthly table that
gains a month each month is normal (38, 39...). A count in the thousands, or an
average partition above a few hundred MB, is not.

**What to do:** do not repartition in the middle of the night. Write down the
numbers and escalate in the morning: changing the grain is a new decision
(ADR). The query is slow but correct.

## Step 4 · Did the data change shape? (3 minutes)

**Why fourth:** same SQL, same partitions, different data.

**Where:** the job's **Execution details** tab (not *Execution graph*). Look at
**Records read** and **Records written** of each stage and compare with the
fast run.

**Gives it away:** *rows in* or *rows out* moved for the same query. On
5 November 2026 the whole fact table was 408,560 lines and the daily grain
356,981 rows. If a load ran twice, the lines double and so does the time.

Check the table directly:

```sql
SELECT COUNT(*) AS n, MIN(order_date) AS first_day, MAX(order_date) AS last_day
FROM `data-engineering-i1.g04_warehouse.orders_plain`;
```

Expected on 5 November: 222,644 rows, 2023-09-15 to 2026-09-14.

**What to do:** if the count moved without a planned load, **do not fix it
yourself.** Tell Till (who owns the extractor) and Jane. A table that doubled
overnight is a data problem, not a query problem.

## Step 5 · Does one stage dominate? (3 minutes)

**Where:** the **Execution details** tab. Each row is a stage (`S00: Input`,
`S01: Join+`, `S02: Output`). Read the **Wait**, **Read**, **Compute** and
**Write** bars.

**Gives it away:** one stage's time is **far above its neighbours**. Example
from the course (3,936 ms, 6 stages): `S03: Join+` took 381 ms, the others
43 to 268 ms. A join or `GROUP BY` shuffles rows so that equal keys meet: that
is usually the slowest stage.

**What to do:**
- If *rows in* is much larger than *rows out* in that stage, **filter before
  the join** (put the `WHERE` in a subquery or CTE on the big table) or
  aggregate before joining.
- If rows in and out are similar, the join itself is the cost. Go on to step 6.

## Step 6 · Is it skew? (3 minutes)

**Where:** in **Execution details**, expand the slow stage. Compare the
**average** and **maximum** of the *Compute* time (Slowest worker).

**Gives it away:** the slowest worker is **far above the average**. The
course's example: average 97 ms, maximum 303 ms, about two thirds of the time
spent waiting for one worker. In our data a few products carry many order
lines: `B0BM4GX6TT` has 1,376 of the 408,560 lines and appears in all 37
months, while `B0CHXWTSM6` has 4.

**What to do:** **a bigger warehouse will not help.** Filter earlier,
aggregate before the join, or break up the hot key. These are changes to the
model: write down the stage, the average and the maximum, and escalate in the
morning.

*We have not seen skew in our own queries yet.* The one join we profiled
(`order_items` joined to three small tables) had an input stage of 15 ms on
average and 63 ms at most: too small to call it. The numbers above are the
course's, not ours.

## When to stop and escalate

- You went through the six steps and found nothing.
- A single query has processed **more than 1 GiB** (about $0.0073). Our whole
  dataset is 0.25 GiB, so that means a bug or a cross join.
- The data itself is wrong: row counts moved, dates out of range, duplicates
  where there were none.
- You need to change a table, a partition grain, or the cap.

**Who:** Enzo for the warehouse (this runbook's author); Till for the extractor
and the data in bronze; Jane for the clickstream. Write in the group chat:
the query, the **bytes processed** now against before, the step you stopped
at, and what you saw. Do not delete tables, views or datasets to "try
something".

## Summary: what gives each cause away

| What is wrong | What gives it away | Step |
|---|---|---|
| Nothing, cached comparison | The fast "before" processed **0 bytes** | 1 |
| Lost its partition filter | **Bytes processed jumped**; the filter is gone or wraps the column | 2 |
| Table outgrew its grain | Partition count or average partition size moved | 3 |
| Data changed shape | **Rows in vs rows out** moved for the same query | 4 |
| One stage dominates | Its time is far above its neighbours in *Execution details* | 5 |
| Skew | Slowest worker far above the average in that stage | 6 |
