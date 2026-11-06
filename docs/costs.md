# Costs

What the platform costs per month, from published prices. Each step adds its
part: the warehouse in step 4 (Enzo), the FinOps review in L09.

## Prices

Read on 3 November 2026 from
[cloud.google.com/storage/pricing](https://cloud.google.com/storage/pricing),
for a bucket in one region, `europe-west1` (Belgium), in USD.

| Class | Storage per GiB-month | Class A per 1,000 | Class B per 1,000 | Retrieval per GiB | Minimum duration |
|---|---|---|---|---|---|
| Standard | $0.020 | $0.005 | $0.0004 | $0 | None |
| Nearline | $0.010 | $0.010 | $0.001 | $0.01 | 30 days |
| Coldline | $0.004 | $0.020 | $0.010 | $0.02 | 90 days |
| Archive | $0.0012 | $0.050 | $0.050 | $0.05 | 365 days |

- Class A operations write and list; Class B operations read.
- A lifecycle class change is one Class A operation, at the rate of the class
  the file moves to.
- Soft-deleted files count as stored until they are purged.

## Step 2: the bronze bucket

Measured on 3 November 2026 with `gcloud storage objects list`:

- **Live files:** 30 objects, 104,128,706 bytes (0.0970 GiB), all Standard.
- **Soft-deleted files:** 28 objects (0.0848 GiB), the files replaced when
  bronze was re-landed that day. The bucket keeps them for 7 days.

| Cost | Calculation | Amount |
|---|---|---|
| Storage, first 30 days | 0.0970 GiB × $0.020 | $0.0019 per month |
| Storage after 30, 90 and 365 days ([lifecycle](../infra/README.md)) | 0.0970 GiB × $0.010, × $0.004, × $0.0012 | $0.0010, $0.0004, $0.0001 per month |
| The replaced files, in soft delete | 0.0848 GiB × $0.020 × 7/30 | $0.0004, once |
| One landing of the export | about 57 Class A (30 uploads, 27 listings) × $0.005 / 1,000 | $0.0003 |
| One full read, in Standard | 30 Class B × $0.0004 / 1,000 | $0.00001 |
| One full read, in Nearline | 0.0970 GiB × $0.01 retrieval | $0.0010 |
| The three class changes | 30 objects × ($0.010 + $0.020 + $0.050) / 1,000 | $0.0024, spread over the first year |

**About $0.003 in the first month,** mostly storage. The external tables in
BigQuery store nothing: queries are billed by bytes processed, measured in
step 4.

## At 100 times the data

| | Today | 100× |
|---|---|---|
| Bytes | 0.097 GiB | 9.7 GiB |
| Objects, with the same layout | 30 | 30 |
| Storage in Standard | $0.0019 per month | $0.19 per month |
| Storage after a year, in Archive | $0.0001 per month | $0.012 per month |
| One landing | $0.0003 | $0.0003 |

- **Storage grows with the bytes. Operations grow with the number of files,**
  and the layout keeps that number fixed: one file per table, `orders` per
  year. A layout by day and product would multiply the files instead
  (Exercise 1: 279× the objects for the same month).
- **Cold files that get read cost more than they save.** Nearline saves $0.010
  per GiB-month and charges $0.01 per GiB read. A job reading all of bronze
  every day would pay 9.7 GiB × $0.01 × 30 = $2.91 per month at 100×, against
  $0.19 for keeping it in Standard. Such a job means changing the lifecycle
  rule.

## Step 4: the BigQuery warehouse

Two meters: **storage** of the native tables and views, and **bytes processed**
by queries. Prices: storage $0.020 per GiB-month, $0.010 after 90 days
untouched; queries $7.50 per TiB in `europe-west1`, the first 1 TiB per month
free. Both from the course's lecture 4, read 24 September 2026; the free tier
confirmed on [cloud.google.com/bigquery/pricing](https://cloud.google.com/bigquery/pricing)
on 5 November 2026 (that page shows $6.25 per TiB for the US regions and no
single Europe row, so we kept the course's figure).

Measured on 5 November 2026 in `g04_warehouse`:

- **15 tables:** 232,719,290 bytes (0.2167 GiB).
- **3 materialised views:** 34,978,600 bytes (0.0326 GiB).

| Cost | Calculation | Amount |
|---|---|---|
| Storage of the tables | 0.2167 GiB × $0.020 | $0.0043 per month |
| Storage of the views | 0.0326 GiB × $0.020 | $0.0007 per month |
| **Storage, first 90 days** | | **$0.0050 per month** |
| Storage after 90 days untouched | 0.2493 GiB × $0.010 | $0.0025 per month |
| Q1, Q2, Q3 tuned ([tuning](warehouse-tuning.md)) | 3,373,224 + 1,000,888 + 4,007,592 bytes ÷ 2^40 × $7.50 | $0.00006 per run of all three |
| One person's working day of building and measuring | 108 SELECT jobs, 925,676,327 bytes ÷ 2^40 × $7.50 | $0.0063, **inside the free tier, so billed $0** |

**About $0.005 per month for the warehouse.** Queries bill nothing: one heavy
day is 0.00084 TiB, and a month of such days is 0.025 TiB against 1 TiB free
([ADR 0004](adr/0004-warehouse-pricing.md)).

- **We keep 15 tables for 7 sources.** The untuned copies and the variants
  (`order_items_day`, `_year_pc`, ...) exist to measure. They cost
  $0.0043 per month together and can be dropped once the tuning page is
  accepted, keeping `orders_month`, `order_items_month_pc` and the lookups.
- **The capped worst case per query** is 104,857,600 bytes ÷ 2^40 × $7.50 =
  $0.0007.
- **At 1,000× the data** the tables would be 249 GiB, $4.99 per month in
  storage, and a full scan 0.24 TiB, $1.83 per query (before the free tier).
  A partition filter and the cap decide whether that happens.
- **Not measured:** the bill itself. We cannot read project-wide billing or
  `JOBS_BY_PROJECT`; the figures come from our own jobs
  (`INFORMATION_SCHEMA.JOBS_BY_USER`).
