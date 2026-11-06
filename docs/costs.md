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

## Step 9: labels, budget and the ledger

### Label convention

Four keys, on every resource Terraform manages, set in
[`infra/terraform/main.tf`](../infra/terraform/main.tf):

| Key | Values | Answers |
|---|---|---|
| `group` | `g04` | Whose is it? The only key that separates us from the other groups in the shared project |
| `environment` | `course` | Is it production? Always `course` here; the key exists so a second environment would not need a new convention |
| `layer` | `bronze`, `warehouse`, `silver`, `gold`, `tfstate` | Which part of the pipeline is it, so a bill can be cut by layer |
| `lesson` | `l02`, `l04`, `l05`, `l08` | Which piece of work created it, so a cost can be traced back to a decision |

Labels are lowercase, with letters, digits, `_` and `-` only (Google's rule:
a value of `None` or a capital is refused, which we met on 6 Nov 2026). We
kept to four keys because every extra key has to be right on every resource,
and nobody checks.

Applied on 6 Nov 2026 at 14:55 UTC. The plan before the apply was
`0 to add, 5 to change, 0 to destroy` and every change was a label added; the
plan after was "No changes". Read back through the Storage and BigQuery APIs:
the data bucket, `g04_bronze_1`, `g04_warehouse`, `g04_silver` and `g04_gold` all
carry the four keys.

**What this does not attribute.**

- **Everything before 6 Nov 2026.** Labels apply forward only: a charge made
  before the label existed is not tagged, and the billing export cannot
  re-tag it. `g04_warehouse` had no label at all until then.
- **Query cost.** A dataset's labels follow its *storage*. The bytes a query
  processes belong to the *job*, and our jobs carry no label: `warehouse/measure.py`
  and dbt do not set one. Query cost is therefore attributed to the project and
  to the person running it (`JOBS_BY_USER`), not to a layer. Not done: adding
  job labels to `measure.py` and to dbt's profile.
- **The state bucket.** `gs://data-engineering-i1-g04-tfstate` is made by hand,
  outside Terraform ([infra](infra.md)), so its labels (`group`, `layer`,
  `environment`, `lesson=l08`) were set by hand too. Nothing detects it if they
  are removed.
- **A label added by hand.** Terraform compares only the labels the code
  declares, so an extra label put on in the console is invisible to the plan
  (shown on 6 Nov, [infra](infra.md), "Drift").
- **`g04_bronze`,** Evaluna's first bronze dataset. It has no label, is not in
  Terraform, and will be deleted. We could not read its size
  (`__TABLES__` is refused).
- **Views.** `g04_silver` holds 13 views (0 bytes) and 1 table (77 bytes). The
  layer label on silver therefore carries almost no storage cost; what silver
  costs is in the bytes its queries read.

### Budget

**Not created. Not done, because the budget API is not available to us.** On
6 Nov 2026 `cloudbilling.googleapis.com` and `billingbudgets.googleapis.com`
both answered 403 "has not been used in project data-engineering-i1 before or
it is disabled". We cannot enable an API on the course project, and we do not
know the billing account's id, so even a `google_billing_budget` in Terraform
could not be written.

What we would set, and who:

- **Named person:** Enzo Méret (`emeret@albertschool.com`) for the group's
  alerts, with Till Lüder as the second recipient.
- **Amount and thresholds:** $1 per month for the group, alerts at 50 %, 90 %
  and 100 %. The current spend is about $0.008 per month (ledger below), so
  $1 is more than 100× what we use: an alert means something is wrong, not that
  we are close.
- **Where:** a budget filtered on the label `group=g04`. This only works for
  the charges that carry the label (storage), not for query jobs (above).

**A budget alert does not stop anything.** It sends an email when a threshold is
crossed; the resources keep running and the charges keep accruing. The only
thing that stops a query today is the cap in `warehouse/measure.py`
(`maximum_bytes_billed`, 100 MiB by default), and it only covers queries run
through that script.

### The largest cost

**Recurring: BigQuery storage in `g04_warehouse`,** $0.0050 per month, 65 % of
the group's $0.0077 monthly total (ledger). SKU: BigQuery *active logical
storage*, billed per GiB-hour. Shape: constant. It grows only when we load or
build a table, and the 7 variant tables are 45 % of it.

**One-off: the query burst of 5 Nov 2026.** Source:
`INFORMATION_SCHEMA.JOBS_BY_USER`, `region-europe-west1`, last 30 days, cache
off, read 6 Nov 2026 (Enzo's own jobs only). Shape: a spike, all on one day.

| Day | Jobs | Bytes processed | Bytes billed | Slot-hours |
|---|---|---|---|---|
| 5 Nov, 124 SELECT | 124 | 942,452,351 | 1,896,873,984 | 0.023 |
| 5 Nov, 15 CREATE TABLE AS SELECT | 15 | 231,231,962 | 262,144,000 | 0.965 |
| 5 Nov, 4 CREATE MATERIALIZED VIEW | 4 | 0 | 0 | none reported |
| 6 Nov, 1 SELECT | 1 | 0 | 0 | 0.00001 |

At $7.50 per TiB that is 1,173,684,313 bytes ÷ 2^40 × $7.50 = **$0.0080 of
processed bytes, $0.0147 on the billed bytes** (billed is larger because each
table read bills at least 10 MiB). **Both are inside the 1 TiB free tier, so
the invoice is $0.** The 15 table builds are 99 % of the slot time (0.965 of
0.988 slot-hours), because a `CREATE TABLE AS SELECT` that reads little still
runs on many slots.

**What we could not use:** the billing export. We cannot read project-wide
billing, so there is no SKU line from the invoice; the SKU above is the one the
pricing page names for this storage, and the query figure comes from units
(bytes), as the brief allows. The jobs cover only Enzo's login, not Till's,
Evaluna's or Jane's.

### One optimisation: drop the seven variant tables (proposed, not done)

`g04_warehouse` keeps seven tables that only exist to measure
([tuning](warehouse-tuning.md)): `order_items_plain`, `_day`, `_month`,
`_year_pc`, `_clustered`, `review_c` and `product_reviews_pc`. No materialised
view and no dbt model reads them: the three views read `order_items_month_pc`
and `orders_plain`, which stay.

| | Before | After |
|---|---|---|
| Bytes in `g04_warehouse` | 267,697,890 (0.2493 GiB) | 145,967,988 (0.1359 GiB) |
| Storage at $0.020 per GiB-month | $0.00499 | $0.00272 |
| **Saving** | | **$0.0023 per month** (121,729,902 bytes) |

Sources: sizes from `__TABLES__` of each dataset, 6 Nov 2026; price from the
course's lecture 4, read 24 Sep 2026. A rebuild is
`warehouse/02_tuned_tables.sql`.

**Not done, because** the group decided not to delete cloud resources for this
saving (Enzo, 6 Nov 2026), and because of the failure conditions below. The
figures are what the saving *would* be.

**When it saves nothing, or goes wrong:**

- **The bill does not move.** BigQuery's first 10 GiB of storage per month is
  free ([pricing](https://cloud.google.com/bigquery/pricing), read 6 Nov 2026).
  We hold 0.31 GiB in total, so the billed saving is $0. The $0.0023 is the
  list price of data we are not charged for.
- **A document points at one.** `docs/runbooks/slow-query.md` names
  `order_items_day` and `orders_month`. Dropping the table breaks its commands.
- **The tuning evidence goes.** The 2.91× and 11.43× figures on the tuning page
  are re-measurable only while those tables exist, or after a rebuild.
- **If the data grows 1,000×,** the variants would be 113 GiB and $2.27 per
  month, and the saving would then be real.

### Ledger

One row per resource. Sizes read 6 Nov 2026 (`__TABLES__` for datasets,
`gcloud`/API listing for buckets). Prices: Cloud Storage from the table above
(read 3 Nov 2026); BigQuery storage $0.020 per GiB-month from the course's
lecture 4 (read 24 Sep 2026). On 6 Nov 2026 the BigQuery pricing page lists
$0.000031507 per GiB-hour for active logical storage, about $0.023 per
GiB-month at 730 hours, but for the regions it lists, which we could not tie to
`europe-west1`. We kept the course's figure.

| Resource | Size | Price used | Per month | Labels |
|---|---|---|---|---|
| `gs://data-engineering-i1-g04` | 104,128,706 bytes (0.0970 GiB), Standard | $0.020 / GiB | $0.0019 | yes |
| `g04_bronze_1` | 0 bytes (28 external tables) | n/a | $0 | yes |
| `g04_warehouse` | 267,697,890 bytes (0.2493 GiB) | $0.020 / GiB | $0.0050 | yes |
| `g04_silver` | 77 bytes (13 views, 1 table) | $0.020 / GiB | $0 | yes |
| `g04_gold` | 42,265,798 bytes (0.0394 GiB) | $0.020 / GiB | $0.0008 | yes |
| `gs://data-engineering-i1-g04-tfstate` | about 21 KB live plus versions | $0.020 / GiB | under $0.00001 | by hand |
| `g04_bronze` (old, to delete) | not readable | n/a | not measured | none |
| Queries | 1,173,684,313 bytes on 5 Nov, 0 since | $7.50 / TiB, 1 TiB free | $0.0080 list, **$0 billed** | none (jobs) |
| **Total, storage** | | | **$0.0077** | |

Everything is below BigQuery's free storage (10 GiB) and query (1 TiB) tiers,
so the group's invoice should be $0 for BigQuery. The bucket has no free tier
in this project that we know of, so $0.0019 is the one real charge. We cannot
confirm it: we cannot read the invoice.
