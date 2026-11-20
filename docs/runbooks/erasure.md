# Runbook: erase one person's data

For whoever receives a deletion request and was not in the room when this was
built. Go in order. Read the next section first: it says what this runbook cannot
do, and one of those limits comes before step 1.

**Who does what** (the separation of duties of [governance](../governance.md)):
the data owner, Till, runs the erasure. Evaluna checks, by counts, that nothing
is left. Nobody checks their own deletion.

**How far it was tested.** On 20 November 2026, on one buyer ("subject A"),
chosen because it has one real order: every count and the dry run on production,
and a real rewrite on a copy of the files. **It has never been run on
production**, and the warehouse `DELETE` and the rebuild after an erasure were not
tested. The figures, times and findings are in
[the test evidence](../evidence/erasure-test.md).

## What you must know before you start

1. **Tonight's extraction restores the person.** The nightly DAG rereads every
   table from the company's database and rewrites `bronze/postgres/<table>/`
   ("each run bronze matches the source", `ingestion/extract_orders.py`). If the
   person is still in the source, they are back in bronze the next night. We do
   not own that database: step 2 is a request to whoever does.
2. **Bronze holds the person in three places, and BigQuery sees two.**
   `bronze/<table>/` (the export), `bronze/postgres/<table>/` (the extractor) and
   `bronze/postgres/_incremental/orders/`. No external table reads the third, so a
   count in BigQuery misses it. In the test, 2 rows of subject A sat there.
3. **Gold has no identifier but still holds the person's purchases.** Its order
   lines carry the `order_id` of the person's orders (6 lines for subject A) until
   gold is rebuilt.
4. **Copies survive after you are done:** 7 days in the bucket, 7 days of time
   travel in BigQuery, and copies on laptops. Step 6 lists them.

## What you need

- `gcloud` and `bq`, logged in (`gcloud auth login` and `gcloud auth
  application-default login`).
- Python 3.12 or later with `pyarrow` (26.0.0 was used): `pip install pyarrow`.
- Write access to the bucket `gs://data-engineering-i1-g04` for the person who
  runs step 3, and read access to the datasets for the person who checks.
- The script [`ingestion/erase_subject.py`](../../ingestion/erase_subject.py) and
  the counts [`erasure-counts.sql`](erasure-counts.sql).

**The identifier never goes in a query text or in a log.** The job history shows
the text of every query to the whole project. So the identifier lives in the
environment variable `SUBJECT_ID`, and BigQuery receives it as a query parameter.
A parameter is not in `INFORMATION_SCHEMA.JOBS` (checked on 20 November 2026), but
the job's configuration, read with `bq show -j <job>`, does show it. It is hidden
better than in the text, not hidden.

## Step 1. Find the person

### 1.1 Get the identifier from the request

`c_id` is the person's identifier. It is the same value as their `buyer_id`, and as
their `seller_id` if they sell. `Read-Host` does not keep what you type in the
shell history:

```powershell
$env:REQUEST_EMAIL = Read-Host "Email of the person"
$env:SUBJECT_ID = (bq --location=europe-west1 query --nouse_legacy_sql --use_cache=false `
  --format=csv --parameter="email::$env:REQUEST_EMAIL" `
  "SELECT c_id FROM ``data-engineering-i1.g04_bronze_1.customer_external`` WHERE email = @email" `
  | Select-Object -Last 1).Trim()
Remove-Item Env:REQUEST_EMAIL
$env:SUBJECT_ID.Length
```

The length must be at least 25 (a customer ID is 25 to 36 characters). If it
prints 4, the email is not in `customer`: stop and check with the person. Never
print `$env:SUBJECT_ID`.

### 1.2 Where the person can be

| Where | Table and column | How it is found |
|---|---|---|
| Bronze, export and extractor | `buyer`, `orders`, `cart`, `returns`, `review`, `wishlist_item`: `buyer_id` | The identifier |
| | `customer`, `customer_shipping`, `customer_payment`, `subscription`: `c_id` | The identifier |
| | `seller`, `seller_products`: `seller_id`; `seller_reviews`: `seller_id` or `review_id` | The identifier, then the review |
| | `order_items`, `shipment`, `payment`: `order_id` | The `order_id` of the person's `orders` |
| | `shipping_details`: `address_id` | The `address_id` of the person's `customer_shipping` |
| | `payment_details`: `payment_id` | The `payment_id` of the person's `customer_payment` |
| | `review_images`, `product_reviews`: `review_id` | The `review_id` of the person's `review` |
| Clickstream | `clickstream`: `buyer_id`; dead letter queue: `raw` | The identifier, and a search of the text |
| Warehouse | `orders_month`, `orders_plain`, `review`: `buyer_id`; `customer_shipping`: `c_id`; `order_items_month_pc`, `shipping_details`, `product_reviews` | The same keys |
| Silver | `stg_orders`, `int_orders`, `int_order_items`, `stg_customer_shipping`, `int_buyer_country`, `stg_review`, `stg_clickstream`: `buyer_id` | The identifier, or its hash once the hashed buyer ID is deployed |
| Gold | `fct_order_items`: `order_id` | The `order_id` of the person's orders |

**Not searched:** free text. `review.r_desc`, `review.title` and `product.p_desc`
can mention a person by name, and only the identifier is looked for. See "Not
handled".

### 1.3 Count before you change anything

Two counts that must agree. Both only read.

```powershell
# In BigQuery: 42 counts, one per table, in about 20 s
cmd /c "bq --location=europe-west1 query --nouse_legacy_sql --use_cache=false --maximum_bytes_billed=2000000000 --max_rows=100 --format=csv --parameter=`"subject::%SUBJECT_ID%`" < docs\runbooks\erasure-counts.sql > counts-before.csv"

# In the files: it reads all of bronze (158 MiB) and took 82 s
python ingestion\erase_subject.py --report dry-run-before.json
```

Keep `counts-before.csv` and `dry-run-before.json`: they hold counts and file
paths, never the identifier. Compare them table by table. In the test they agreed
on every table except one difference: `bronze/postgres/_incremental/orders/` had
2 rows that BigQuery did not count. A difference is a finding: note it.

## Step 2. The source

Ask the owner of the company's database to delete the person from it, and wait for
their answer. Until then, step 3 can be undone by the next extraction.

If you cannot wait, stop the two things that put the person back, then restart
them once the source is clean:

```powershell
cd orchestration
docker compose exec -T airflow-scheduler airflow dags pause g04_marketplace_daily   # the nightly extraction, 02:00 UTC
cd ..
docker compose -f ingestion/compose.yaml stop                                       # the clickstream consumer
```

Not tested: neither command was run during the test.

Two more places put the person back, and both are on laptops, not in the cloud:
the CSV export (`legacy_csv`) and the `out/` folder of `land_export.py`.
Rerunning `land_export.py --upload` lands the export's rows again. Delete the
person's rows from those files, or the files.

## Step 3. Bronze (run by Till)

### 3.1 Dry run

Count what would be removed, file by file. This is the default: it writes nothing.

```powershell
python ingestion\erase_subject.py --report dry-run.json
```

### 3.2 Rewrite

```powershell
python ingestion\erase_subject.py --apply --production --report apply.json
```

For each file that holds rows of the person, the script rewrites the file without
them, reads it back, checks that no row of the person is left and that the other
rows are all there, then counts every table again. It stops with an error if one
check fails. Without `--production` it refuses to write on `bronze/`, so a test on
a copy (`--prefix gs://.../test-erasure`) is safe.

**It was never run on production.** On a copy of 21 files (125 MB), the rewrite
and the final count took 141 s, and removed 59 rows. Step 3.1 on all of bronze
took 82 s.

### 3.3 What changes and what does not

- A rewritten file is a new version of the object. The previous version stays in
  the bucket for 7 days (step 6).
- A file whose rows all belong to the person is rewritten empty, so that the
  external tables still read it.
- The external tables need no change: they read the files, and the paths are the
  same.
- If the person is a seller (`seller_id`), the same identifier is searched in the
  seller tables.

## Step 4. The warehouse (Enzo's dataset)

`g04_warehouse` holds the person in native tables that dbt does not rebuild.
Count first, with the counts from step 1.3 (the "warehouse" lines). Then delete.

**Not tested. These statements were never run; the counts above were.** Children
before parents, so that the keys can still be read:

```sql
DECLARE sid STRING DEFAULT @subject;
DELETE FROM `data-engineering-i1.g04_warehouse.order_items_month_pc`
  WHERE order_id IN (SELECT order_id FROM `data-engineering-i1.g04_warehouse.orders_plain` WHERE buyer_id = sid);
DELETE FROM `data-engineering-i1.g04_warehouse.shipping_details`
  WHERE address_id IN (SELECT address_id FROM `data-engineering-i1.g04_warehouse.customer_shipping` WHERE c_id = sid);
DELETE FROM `data-engineering-i1.g04_warehouse.product_reviews`
  WHERE review_id IN (SELECT review_id FROM `data-engineering-i1.g04_warehouse.review` WHERE buyer_id = sid);
DELETE FROM `data-engineering-i1.g04_warehouse.orders_month` WHERE buyer_id = sid;
DELETE FROM `data-engineering-i1.g04_warehouse.orders_plain` WHERE buyer_id = sid;
DELETE FROM `data-engineering-i1.g04_warehouse.review` WHERE buyer_id = sid;
DELETE FROM `data-engineering-i1.g04_warehouse.customer_shipping` WHERE c_id = sid;
```

Pass the identifier as a parameter, as in step 1.3. Three things to check with
Enzo before running it: that BigQuery accepts a `DELETE` on a table that a
materialised view reads (`daily_demand_country_mv` reads `orders_plain`,
`customer_shipping`, `shipping_details` and `order_items_month_pc`), whether the
view is refreshed by it, and that this is cheaper than rebuilding the tables with
`warehouse/01_load_native_tables.sql` and `02_tuned_tables.sql`. A rebuild with
`CREATE OR REPLACE TABLE` also drops any policy tag on the table.

## Step 5. Silver and gold

**Silver.** Today the silver models are views over the bronze files, so once step
3 is done they no longer return the person, and there is nothing to rebuild. When
the hashed buyer ID is deployed, `stg_orders` and `stg_customer_shipping` become
tables: they need the rebuild below.

**Gold.** Its tables are built by dbt and must be rebuilt, after step 3, or they
keep the person's order lines and their share of the totals. The nightly DAG does
it (`dbt_build`); to do it now, with the image tag set in
`orchestration/dags/marketplace_g04.py`:

```powershell
docker run --rm `
  -v C:/Users/<you>/AppData/Roaming/gcloud/application_default_credentials.json:/gcloud/adc.json:ro `
  -e GOOGLE_APPLICATION_CREDENTIALS=/gcloud/adc.json `
  docker.io/jgalthie/group4-transform:<TAG> build
```

On macOS the credentials file is `$HOME/.config/gcloud/application_default_credentials.json`.
It rebuilds the five gold tables (`fct_order_items`, `fct_daily_demand`,
`dim_country`, `dim_date`, `dim_product`), the silver tables and the seed, and
runs the tests: about 40 s (39.57 s on a test target, 19 November 2026). It
rebuilds everything, so the aggregates (units, revenue, number of buyers per
country) lose the person's share without any way to tell which share it was.

Gold has no `buyer_id`, so check it by the orders: before the rebuild, count the
person's order lines (6 for subject A, `erasure-counts.sql`); after it, the same
count must be 0.

## Step 6. The copies that survive

None of these is removed by steps 3 to 5.

| Copy | How long | Can it be removed earlier? |
|---|---|---|
| The previous version of every file rewritten in step 3 | 7 days in the bucket (`soft delete`, 604,800 s). Versioning is off. In the test: 42 versions, 250,019,612 bytes, deleted for good between 27 November 10:12:24 and 10:17:21 UTC | No command found. `gcloud storage rm` has no option for it, and `buckets update --clear-soft-delete` "does not affect objects already in soft-deleted state". Not tested |
| BigQuery time travel on `g04_silver`, `g04_gold`, `g04_warehouse` | 168 hours (7 days), then a fail-safe period that we cannot read | The window is `max_time_travel_hours` on the dataset. We did not change it |
| The test copies in `test-erasure/` | Same 7 days after their deletion. They hold whole tables of real data, not one person | No |
| The CSV export and the `out/` folders on laptops | Until someone deletes them | Only by hand, on each laptop |
| The Kafka topic `clickstream` | 7 days | Kafka deletes by age |
| The job history | Not checked | The counts only show tables and numbers, and the identifier is a parameter (see above) |
| Airflow and dbt logs | Not checked | Not checked |

To shorten what we control, set a shorter soft delete on the bucket and a shorter
time travel window on the datasets. A shorter soft delete applies to objects
deleted later, not to those already deleted. We did not do it, and
[ADR 0010](../adr/0010-data-classification.md) is where it is decided.

## Step 7. Prove it

The person who checks is not the person who deleted.

1. Run the two counts of step 1.3 again, to `counts-after.csv` and
   `dry-run-after.json`. Every line must say 0, except the copies of step 6.
2. Count the person's order lines in gold again: 0.
3. Compare with the "before" files: every table that had rows now has none, and
   the number of rows lost in each file is the number the dry run announced.
4. Write the proof: the date, the request number (not the identifier, not the
   email), the two counts, the times, and what survives with its date of
   deletion. The test evidence is the model.
5. Remove what you kept: `Remove-Item Env:SUBJECT_ID`, and the `counts-*.csv` and
   `*.json` files if they are not needed.

**What the proof does not show:** that the source no longer holds the person, that
the copies of step 6 are gone, and that free text does not mention them.

## Not handled

| What | Why |
|---|---|
| The company's database | It is not ours (step 2) |
| Free text that names the person | Only the identifier is searched. `r_desc`, `title`, `p_desc` and `raw` are unclassified: we cannot tell what they hold |
| The old versions in the bucket | 7 days, and no way to purge them found |
| BigQuery time travel and fail-safe | 7 days, plus a period we cannot see |
| Laptops | CSV export, `out/` folders, Docker volumes |
| The warehouse `DELETE` | Never run (step 4) |
| The pause of the DAG and of the consumer | Never run (step 2) |
| Hashed silver | The tables are not deployed. The count of the hash has not been run |
| An erasure on production | Never done. It would remove real rows from gold, which the team uses, and the next extraction restores the person while the source holds them. The data owner runs it, when a real request exists |
