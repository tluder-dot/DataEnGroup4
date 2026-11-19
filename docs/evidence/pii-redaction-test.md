# Evidence: the hashed buyer ID, tested before it reaches production

A test build of the dbt project with `buyer_id` replaced by a salted hash,
compared with production. Branch `transform/pii-redaction`, commits `87ae33b`
to `92dea93`. Run on 19 November 2026. All times are UTC, read from BigQuery's
clock (`SELECT CURRENT_TIMESTAMP()`), not from the laptop's.

## What was tested

The change: `stg_orders` and `stg_customer_shipping` hash the buyer ID with
`pseudonymise()` and become tables; `stg_review` and `stg_clickstream` drop
`buyer_id`. The salt is read from a table, so it is in no SQL text
([ADR 0010](../adr/0010-data-classification.md), to come).

The test never touched `g04_silver` or `g04_gold`. It wrote only to two
datasets made for it, `g04_test_silver` and `g04_test_gold`, with the salt of
the test in `g04_test_silver.pii_salt`. That salt was 64 hex characters from the
system's random generator, kept in memory, never printed or written to a file,
and deleted with the dataset.

## How

| Step | What | When (UTC) |
|---|---|---|
| Create the datasets | `bq mk --dataset` with labels `group=g04`, `environment=test`, `layer`, `lesson=l10`, tables expiring after 1 day | 19 Nov |
| Remove the default groups | `projectReaders` and `projectWriters` taken off both; `bq show` then listed only `projectOwners` and the owner's login | 19 Nov |
| Write the test salt | `seed_pii_salt.py --dataset g04_test_silver`, run in the image; job `778c4e67-9353-474c-b028-58fa0508ca34` | 19 Nov |
| Read production gold | Two queries, cache off, cap 100 MiB | 18:45:19 and 18:45:25 |
| Build | `dbt build --vars "{salt_dataset: g04_test_silver}"` with `DBT_DATASET=g04_test`, image built locally from the branch (dbt 1.12.6, adapter bigquery 1.12.1) | 18:45:34 to 18:46:12 |
| Compare | Same queries on `g04_test_gold`, then row by row | After the build |
| Delete | `bq rm -r -d -f` on both datasets, then `bq ls` no longer listed them; local image removed | 19 Nov, done before 18:52:03 (BigQuery's clock at the check) |

Before the build, `dbt ls` listed the 19 models and seeds with the dataset each
writes to: all in `g04_test_silver` or `g04_test_gold`. The sources it reads were
the 9 tables of `g04_bronze_1` and `g04_test_silver.pii_salt`. No hook is set.

**Nothing else wrote to production meanwhile.** `INFORMATION_SCHEMA.JOBS_BY_PROJECT`,
last 30 minutes before 18:46 UTC: no job wrote to `g04_silver` or `g04_gold`.
Production gold had been read once before, at 18:21:17 and 18:21:21, and gave the
same figures.

## The build

`PASS=81 WARN=3 ERROR=0 SKIP=0 NO-OP=0 TOTAL=84` in 39.57 s: 1 seed, 7 table
models, 11 view models, 64 data tests and 1 unit test.

The three warnings are the known ones:

| Test | Rows | Meaning |
|---|---|---|
| `not_null_dim_product_product_name` | 6 | Products with no name |
| `assert_line_revenue_is_positive` | 15 | Order lines that round to 0.00 |
| `assert_lines_without_country` | 67 | Lines of buyers with no address (16 on 6 November: it grows with the data) |

Cost: `INFORMATION_SCHEMA.JOBS_BY_USER`, cache off, jobs touching the two test
datasets between 18:45:26 and 18:46:40: 65 jobs, 480,159,088 bytes processed,
0 failed.

## Gold, test against production

These are not the 111,318 orders and EUR 19,599,891.62 of
[acceptance criteria](../acceptance-criteria.md): those are the export's. Gold now
reads the extractor's tables, so the test is compared with production gold as
read at 18:45.

| | Production (18:45:19) | Test | Difference |
|---|---|---|---|
| Distinct orders, `fct_order_items` | 115,175 | 115,175 | 0 |
| Units | 717,404 | 717,404 | 0 |
| Revenue | 20,261,896.25 | 20,261,896.25 | 0 |
| Lines | 211,446 | 211,446 | 0 |
| Units, `fct_daily_demand` | 717,404 | 717,404 | 0 |
| Revenue, `fct_daily_demand` | 20,261,896.25 | 20,261,896.25 | 0 |
| Buyers, `dim_country` | 100,000 | 100,000 | 0 |
| Products, `dim_product` | 42,858 | 42,858 | 0 |

Row by row, `SELECT * ... EXCEPT DISTINCT` in both directions:

| Table | Only in test | Only in production | Rows (both) |
|---|---|---|---|
| `fct_order_items` | 0 | 0 | 211,446 |
| `fct_daily_demand` | 0 | 0 | 210,530 |
| `dim_country` | 0 | 0 | 7 |
| `dim_date` | 0 | 0 | 1,112 |
| `dim_product` | **1** | **1** | 42,858 |

### The one difference

Product `B011JG1K3E`: `avg_rating` is 3.337 in the test and 3.338 in production,
with 80 reviews on both sides. Its ratings add up to 267, so the average is
exactly 267 / 80 = 3.3375, a tie, and `ROUND(AVG(rating), 3)` on a floating point
number can land on either side.

- Production silver (`g04_silver.int_product_ratings`) run 3 times on 19 November
  gives 3.337, like the test.
- Production gold was built at 13:23 UTC the same day and holds 3.338. We do not
  know why it differs.
- The branch touches neither `int_product_ratings` nor the ratings
  (`git diff main` is empty on `models/intermediate/` and `models/marts/`).

So the difference is in an existing model and is not caused by this change.

## Pseudonymisation

Counts on `g04_test_silver` and `g04_silver`, cache off.

| Check | Result |
|---|---|
| Distinct buyer IDs in `stg_orders`: production (real) and test (hashed) | 100,046 and 100,046 |
| Rows of `stg_orders` | 226,508 and 226,508 |
| Distinct IDs in `stg_customer_shipping` | 100,000 and 100,000 |
| Hashed IDs equal to a real ID | 0 |
| IDs that are not 64 lowercase hex characters (orders, shipping) | 0 and 0 |
| Length of a hashed ID, minimum and maximum | 64 and 64 |
| Tables or views with a `buyer_id` column | `stg_orders`, `stg_customer_shipping`, `int_orders`, `int_order_items`, `int_buyer_country`: all hashed |
| `buyer_id` in `stg_review` and `stg_clickstream` | Gone |
| View definitions holding a 64 hex character literal, or naming the salt table | None of the 11 views |
| `stg_orders` and `stg_customer_shipping` | Tables. The rest of silver is views |

The hash keeps one ID to one hash, so the joins still work, and gold is
unchanged.

## What this does not show

- **A hash is still personal data.** It is a pseudonym (GDPR Art. 4(5)).
- **Bronze still holds the real IDs.** Only readers of silver are protected.
- **The salt is only as secret as the table.** A project-level role reads every
  dataset ([governance](../governance.md), gap 10), so anyone with it reads the
  salt too. Anyone who has the salt and the public list of buyer IDs can
  recompute every hash.
- **Production has no real salt yet.** The test used a throwaway one. The real
  salt waits for the dataset `g04_secrets`, which Terraform will create.
- **One run, one day of data.** A different day, a different salt or a rebuilt
  production gold could differ by a rounding tie like the one above.
