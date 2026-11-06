# Warehouse tuning (step 4)

What we loaded into BigQuery, how we shaped the tables, what each change saved
and what it did not, and how the spend is capped.

**How every figure here was measured** (5 November 2026, dataset
`data-engineering-i1.g04_warehouse`, `europe-west1`):

- **Query cache off** (`use_query_cache=False`; in the console, *Query
  settings → Use cached results* unticked). With the cache on, a rerun of the
  same query reported 0 bytes (measured: 1,000,888 bytes, then 0 with
  `cache_hit = True`).
- **Bytes processed, never bytes billed.** Billing rounds up to 10 MiB per
  table, so on tables this small every query bills 10,485,760 bytes or more
  and the ratios vanish.
- **Dry run first, then run.** [`warehouse/measure.py`](../warehouse/measure.py)
  does both and prints the cost at $7.50 per TiB (the course's lecture 4, read
  24 September 2026). For the tables without clustering the two numbers
  matched every time. **For clustered tables they did not:** the dry run
  reports an upper bound that ignores clustering (8,171,200 bytes) while the
  run processed 380,220. So the clustering rows below are *run* figures.
- **The SQL is in the repo:** [`warehouse/01_load_native_tables.sql`](../warehouse/01_load_native_tables.sql),
  [`warehouse/02_tuned_tables.sql`](../warehouse/02_tuned_tables.sql),
  [`warehouse/daily_demand.sql`](../warehouse/daily_demand.sql).
- **Dates:** "today" is `DATE '2026-09-14'`, the last order in the export.
  Last twelve months = 2025-09-15 to 2026-09-14; last quarter = 2026-06-15 to
  2026-09-14.

**After this step the numbers are still wrong.** The tables hold bronze as it
arrived: every order is there twice. Q1 below returns 74,417 orders and
€13,065,805.92 for the last twelve months, the "export as is" figure of the
course. Tuning answers *how fast and how much*, not *is it true*. That is
silver, in L05.

## 1. What we loaded, and what stayed external

Seven tables, as native tables in `g04_warehouse`. The row counts match the
data dictionary.

| Table | Rows | Bytes (logical) | Notes |
|---|---|---|---|
| `orders_plain` | 222,644 | 15,585,808 | Untuned copy. `order_date` runs 2023-09-15 to 2026-09-14 |
| `order_items_plain` | 408,560 | 17,976,640 | `order_items` joined to `orders` for `order_date`: **the first line of silver.** The join lost no row (408,560 in, 408,560 out, 0 null dates) |
| `review` | 111,322 | 28,729,686 | `r_desc` is free text and most of the bytes |
| `product_reviews` | 111,322 | 3,117,016 | |
| `product` | 42,858 | 15,339,986 | |
| `customer_shipping` | 200,001 | 9,800,083 | `is_default` is text (`'0'`, `'1'`), not a number |
| `shipping_details` | 200,001 | 4,854,361 | **Only `address_id` and `country`.** Street, zip and phone are personal data that no query here needs ([data dictionary](data-dictionary.md)), so they are not copied |

Columns are named in every load. Nothing is cleaned: the duplicates and
`csv_index` come along, and silver removes them once.

**Left external, on purpose:** the other 20 tables of `g04_bronze_1`, the
clickstream and the whole bucket. Nothing in the project queries them, and
bronze is the archive we replay from: written once, read rarely. Loading it
would pay warehouse prices for a second copy of the truth. The comparison that
settles it for the seven tables we *do* query:

| Query | External table | Native table | |
|---|---|---|---|
| Orders per month, from 2025-09-15 | 952,680 bytes, 303 to 331 ms, 176 to 344 slot-ms | 1,781,152 bytes, 107 to 266 ms, 8 to 11 slot-ms | Native is **about 3× faster** and uses **16 to 43× less slot time** |
| `AVG(rating)` over `review` | 890,576 bytes, 197 to 316 ms | 890,576 bytes, 95 to 114 ms | Same bytes, 2 to 3× faster |

The byte counts differ (952,680 against 1,781,152) because the external table
counts compressed Parquet and the native one counts logical bytes. **Do not
compare them.** A second difference matters for the cap: **the dry run of an
external table reports 0 bytes,** so it cannot warn you before you run.

## 2. Partitioning and clustering

All rows are *bytes processed, cache off*. "Before" is the untuned copy.

### The tuning table

| Table | Change | Query | Bytes before | Bytes after | Ratio |
|---|---|---|---|---|---|
| `orders` | `PARTITION BY DATE_TRUNC(order_date, MONTH)` | Orders per month, from 2025-09-15 | 1,781,152 | 616,440 | **2.89×** |
| `order_items` | partition by month | Q1 revenue by month, last 12 months | 9,805,440 | 3,373,224 | **2.91×** |
| `order_items` | partition by **day** + cluster `p_id` | Q1 | 9,805,440 | 3,256,368 | 3.01× |
| `order_items` | partition by month | Q2 top 10 products, last quarter | 11,439,680 | 1,000,888 | **11.43×** |
| `order_items` | partition by month + cluster `p_id` | Q2 | 1,000,888 (month only) | 1,000,888 | **1.00×** |
| `order_items` | cluster `p_id` only | Q2 | 11,439,680 | 11,439,680 | **1.00×** |
| `order_items` | partition by day + cluster | Q2 | 1,000,888 (month) | 850,528 | 1.18× |
| `order_items` | partition by year + cluster | Q2 | 1,000,888 (month) | 2,304,680 | **0.43×** (worse) |
| `order_items` | cluster `p_id` only | `SUM(qty) WHERE p_id = 'B0CHXWTSM6'` | 8,171,200 | 8,171,200 | **1.00×** |
| `order_items` | partition by month, no cluster | same | 8,171,200 | 8,171,200 | **1.00×** |
| `order_items` | partition by month + cluster | same | 8,171,200 | 380,220 | **21.5×** |
| `order_items` | partition by day + cluster | same | 8,171,200 | 25,900 | 315× |
| `order_items` | partition by year + cluster | same | 8,171,200 | 80 | 102,140× |
| `order_items` | month + cluster | same, **best seller** `B0BM4GX6TT` (1,376 lines, in all 37 months) | 8,171,200 | 8,171,160 | **1.00×** |
| `product_reviews`, `review` | cluster `p_id`, `review_id` | Q3 average rating, more than 50 reviews | 4,007,592 | 4,007,592 | **1.00×** |

### Partition grain: month, defended

| Layout of `order_items` | Partitions | Average partition |
|---|---|---|
| none | 1 | 17,976,640 bytes |
| by year | 4 | 4,494,160 |
| **by month** | **37** | **485,855** |
| by day | 1,096 | 16,402 |

(`INFORMATION_SCHEMA.PARTITIONS`, 5 November.) We chose **month** for four reasons:

1. **The filters are months and quarters.** Q1 and Q2 filter on a date range.
   Month reads 1.0 MB for Q2; year reads 2.3 MB (2.3× more) because it cannot
   skip the other three quarters of 2026.
2. **Day buys almost no bytes and costs time.** Day saved 15% on Q2 (850,528
   against 1,000,888) and 3% on Q1, but its 1,096 partitions are 16 KB each.
   Repeated runs: Q2 on day took 182 to 224 ms and 488 to 785 slot-ms, against
   103 to 133 ms and 38 to 49 slot-ms on month (**about 15× the slot time**).
   `SUM(qty)` for one product took 671 to 925 ms on day + cluster against 109
   to 119 ms on month + cluster. It is the over-partitioning of lesson 2 again.
3. **The date range of the project is three years.** 37 monthly partitions
   cover it; the table grows by one partition a month.
4. **It matches the star sketch,** whose grain is a day but whose reports are
   monthly ([star schema](model/star-daily-demand.md)).

**The honest limit:** Google says tables and partitions under 64 MB gain little
from partitioning. Our whole table is 17 MB and the average partition 0.46 MB.
The ratios are real and the money is nil: every query here costs less than
$0.0001. We tune to learn the method and because the table will grow, not to
save money today.

### What clustering did, and did not do

- **Cluster alone: 1.00×.** `CLUSTER BY p_id` with no partition read the same
  8,171,200 bytes for one product. One partition with all the values spread
  over every block: nothing to skip.
- **Cluster on top of month: 21.5×, but only for a rare product.**
  `B0CHXWTSM6` has 4 lines in 2 of 37 months. The best seller `B0BM4GX6TT` has
  1,376 lines in all 37 months and read 8,171,160 bytes: **1.00×.** Clustering
  saves in proportion to how few blocks hold the value.
- **Q2 did not gain from clustering (1.00×)** because it ranks all products
  and filters on no `p_id`. Clustering sorts rows *inside* a partition, and Q2
  needs all of them.
- **Q3 has no date,** so partitioning cannot help, and clustering on the join
  and group keys saved nothing either (1.00×): it reads two small tables whole.
- **This differs from the lecture.** The lecture reports that only month +
  cluster saved on `B0CHXWTSM6`. We measured savings on day and year too (25,900
  and 80 bytes). We did not find out why; it may depend on how the load ordered
  the rows. We therefore did not choose the grain from this query: we chose it
  from Q1, Q2 and the partition sizes, and the best-seller row shows that the
  one-product result does not generalise.
- **Dry-run limitation, repeated:** a dry run showed 8,171,200 for all of them.
  Only running the query shows the saving.

### Column pruning

Not a tuning step, but the biggest single lever, and free:

| Query on `review` | Bytes | |
|---|---|---|
| `r_desc`, `title` and 5 other columns | 28,729,686 | |
| same, with `LIMIT 10` | 28,729,686 | **`LIMIT` does not cut the bill** |
| `review_id`, `rating` only | 1,781,152 | **16.1× less** |

### Filters that stop pruning

On `order_items_month_pc` (month partitions), selecting `p_id` and `qty`:

| Filter on `order_date` | Bytes | Pruned? |
|---|---|---|
| `>= DATE '2026-06-15' AND <= DATE '2026-09-14'` | 1,000,888 | Yes |
| none | 3,302,820 | n/a |
| `FORMAT_DATE('%Y-%m', order_date) >= '2026-06'` | 9,995,468 | **No, and it reads `order_date` too: 3× the no-filter cost** |
| `IN (SELECT DATE '2026-09-14')` | 11,439,680 | No |
| dates supplied by a `JOIN` to `orders` | 15,001,984 | No |

Rule: it prunes when the range is known before the query reads, so compare the
column to a constant.

## 3. Three analytical queries the project needs

Cost = bytes ÷ 2^40 × $7.50. The first 1 TiB per month is free, so **none of
these is ever billed.**

| # | Question, and who asks it | Table | Bytes processed | Cost | Tuned vs untuned |
|---|---|---|---|---|---|
| Q1 | Revenue by month, last 12 months (the revenue reports) | `order_items_plain` | 9,805,440 | $0.0000669 | |
| | | `order_items_month` | 3,373,224 | $0.0000230 | **2.91×** |
| Q2 | Top 10 products by units, last quarter (analysts) | `order_items_plain` | 11,439,680 | $0.0000780 | |
| | | `order_items_month` | 1,000,888 | $0.0000068 | **11.43×** |
| | | `order_items_month_pc` | 1,000,888 | $0.0000068 | 1.00× over month |
| Q3 | Average rating per product with more than 50 reviews (product team) | `product_reviews` + `review` | 4,007,592 | $0.0000273 | |
| | | clustered copies | 4,007,592 | $0.0000273 | **1.00×** |

```sql
-- Q1
SELECT DATE_TRUNC(order_date, MONTH) AS month, SUM(qty * price_at_purchase) AS revenue
FROM `data-engineering-i1.g04_warehouse.order_items_month`
WHERE order_date >= DATE '2025-09-15' AND order_date <= DATE '2026-09-14'
GROUP BY month ORDER BY month;

-- Q2
SELECT p_id, SUM(qty) AS units
FROM `data-engineering-i1.g04_warehouse.order_items_month`
WHERE order_date >= DATE '2026-06-15' AND order_date <= DATE '2026-09-14'
GROUP BY p_id ORDER BY units DESC LIMIT 10;

-- Q3
SELECT pr.p_id, AVG(r.rating) AS avg_rating, COUNT(*) AS n_reviews
FROM `data-engineering-i1.g04_warehouse.product_reviews` AS pr
JOIN `data-engineering-i1.g04_warehouse.review` AS r USING (review_id)
GROUP BY pr.p_id HAVING COUNT(*) > 50 ORDER BY avg_rating DESC;
```

- **Q1** gains 2.91× because the filter is a constant range and the table has
  37 partitions to skip down to 12.
- **Q2** gains 11.43× for the same reason, on a 3-month window.
- **Q3** gains nothing: it has no date, and it reads two small tables whole.
  Measured 1.00×.
- **Q1's answer is wrong** (74,417 orders, €13,065,805.92, with every order
  counted twice). Its cost is right.

## 4. The daily demand materialised view

[`warehouse/daily_demand.sql`](../warehouse/daily_demand.sql). The ML team asks
for units per product, per country, per day.

### Collapse ratio = order lines ÷ distinct groups

Computed on the joined fact (408,560 lines, each resolved to the buyer's default
country; the join loses no line):

| Grain | Distinct rows | Collapse ratio |
|---|---|---|
| fact table | 408,560 | 1.00 |
| product × day | 356,981 | **1.14** |
| product × country × day (**the star's grain**) | 365,512 | **1.12** |
| product × country × month | 196,400 | 2.08 |
| product × month | 165,141 | **2.47** |
| product | 41,323 | 9.89 |

Check: Σ units = 1,386,640 in the view and in the table; Σ revenue =
39,199,900.62 in both.

### What the view saves

| Query | Bytes processed | |
|---|---|---|
| Daily aggregate from `order_items_month`, no view on it | 14,708,160 | |
| Same query on `order_items_month_pc`, **BigQuery rewrote it to the view** | 12,851,316 | **1.14× fewer** |
| Reading `daily_demand_mv` directly | 12,851,316 | the view is 12,851,316 bytes |
| Monthly aggregate, no view | 14,708,160 | |
| Reading `monthly_demand_mv` | 5,945,076 | **2.47× fewer** |

- **At the star's grain the view does almost nothing.** The ratio is 1.12 to
  1.14 and the saving is 12.6% of one query: 1,856,844 bytes, or $0.0000127.
  Under per-byte billing it is nearly nothing, because the aggregate is almost
  as big as the table.
- **A coarser grain moves the ratio, as the lecture predicts.** Product ×
  month gives 2.47, and the monthly view reads 2.47× fewer bytes (5,945,076
  against 14,708,160). The ratio *is* the byte saving.
- **The country view is worse than no view for a window.** The ML query for
  the last 30 days read 20,580,028 bytes from the base tables, 20,508,083 when
  BigQuery used the view automatically (0.3% less), and **36,097,836 reading
  the view directly** (1.75× more): the view is not partitioned, and reading it
  cannot skip months. (The same read gave 33,173,740 earlier the same day,
  before the views had settled; we did not find out why the figure moved.) A partitioned version of the view was accepted by
  BigQuery, read 20,401,147 bytes for the same window (0.9% less than the base
  tables), and we dropped it.

**What it costs.** Storage of the three views: 34,978,600 bytes, $0.0007 per
month at $0.020 per GiB. BigQuery refreshes them every 30 minutes
(`refresh_interval_minutes = 30`); the base table does not change between
loads, so there is nothing to refresh today. BigQuery restricts the aggregates and joins a view may use (lecture 4); it
accepted our three-join `GROUP BY`.

**What we keep and why.** We keep `daily_demand_country_mv` because it is the
ML team's grain and one place for the country rule, **not because it saves
bytes.** We say so rather than claim a saving. Its value is a named, shared
definition, which silver and gold will carry as a tested dbt model in L05.
`daily_demand_mv` and `monthly_demand_mv` stay as the measurements above.

## 5. The cap: `maximum_bytes_billed`

| Where | Value | Why |
|---|---|---|
| **Each query, in [`warehouse/measure.py`](../warehouse/measure.py)** | 104,857,600 bytes (100 MiB) | See below |
| **Each query, in the console** | *More → Query settings → Advanced options → Maximum bytes billed* | Set it by hand before an exploratory query |
| Project default | **Not set** | The project is shared by the cohort, and we did not try to change project-level quotas. In L05 the dbt profile has a `maximum_bytes_billed` field that applies to every model |

**The value.** The ML query for a window of 30 days (the fact and three small
tables) processed 20.4 MB but needed a cap of
**41,943,040 bytes (40 MiB)** to run: with 10 MiB and 20 MiB it failed, with 40
MiB it ran. The reason is the 10 MiB minimum per table: the cap applies to
billed bytes. 100 MiB is 2.5× that, and its worst case is
104,857,600 ÷ 2^40 × $7.50 = **$0.0007 per query.** Without a cap the worst
case is the whole dataset: 0.25 GiB, about $0.0018. The cap matters little at
this size and a great deal at 1,000× the data, so we set it now.

**The error, copied exactly** (cap of 1,000,000 on a scan of `order_items_plain`):

```
Query exceeded limit for bytes billed: 1000000. 10485760 or higher required.
```

- **It cost nothing:** the failed job has no `total_bytes_billed`.
- **Raised to 10485760 it ran:** 8,171,200 bytes processed, 10,485,760 billed.
  10,485,760 = 10 MiB, the minimum billing for one table.
- With the cap at 10 MiB or 20 MiB the three-table ML query failed with
  `...Query exceeded limit for bytes billed: 10485760. 41943040 or higher
  required.`

## Not done, and why

- **`require_partition_filter`** is not set on the partitioned copies. It would
  reject any query without a date filter, which is right for the fact table and
  wrong for the lookup tables. It belongs on the silver fact table in L05.
- **No test of the capacity pricing.** [ADR 0004](adr/0004-warehouse-pricing.md)
  does the arithmetic from list prices. We did not create a reservation.
- **The execution graph of a slow query** was read on one join (two stages,
  slowest worker 63 ms against an average of 15 ms in the input stage). That is
  too small to call skew. The [runbook](runbooks/slow-query.md) uses the
  lecture's example for the skew case and says so.
- **Timings are noisy.** One user, small tables, a few repeats each. We report
  ranges and lean on bytes and slot-milliseconds, which repeat.
