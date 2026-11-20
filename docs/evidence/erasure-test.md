# Evidence: the erasure runbook, tested on subject A

What was run, on 20 November 2026, to test [the erasure runbook](../runbooks/erasure.md),
and what it showed. All times are UTC, read from BigQuery's clock. The person is
called "subject A": the identifier is in no file of this repository, in no query
text and in no output. It was passed in the environment variable `SUBJECT_ID`, and
the output and the report of each run were searched for it afterwards (not found).

**Production was not changed.** Every count and the dry run read production. The
only write was a rewrite of a copy of 21 files, in `gs://data-engineering-i1-g04/test-erasure/`.
Why no real erasure on production: the next nightly extraction restores the person
from the source, gold is used by the team, and the data owner runs a real erasure
when a real request exists.

## The person

Subject A is a buyer with one real order (`int_orders` has 1 row), at least one
review, an address, and clickstream events. It was chosen by a query that ranks the
candidates by a fingerprint of the identifier and takes the first, so the choice is
repeatable: 4,790 buyers matched. The query did not return the identifier to the
screen.

## Counts in BigQuery, before

`docs/runbooks/erasure-counts.sql`, 20 November, 09:52:27 to 09:52:50 (19.2 s),
cache off, 42 counts, 7 of them 0. Only the tables that hold rows:

| Layer | Table | Rows |
|---|---|---|
| Bronze, export | `buyer_external` | 1 |
| | `customer_external` | 1 |
| | `customer_payment_external` | 1 |
| | `customer_shipping_external` | 1 |
| | `orders_external` | 2 (the order and its twin) |
| | `order_items_external` (by order) | 12 |
| | `shipment_external` (by order) | 12 |
| | `payment_external` (by order) | 2 |
| | `payment_details_external` (by payment) | 1 |
| | `shipping_details_external` (by address) | 1 |
| | `review_external` | 1 |
| | `product_reviews_external` (by review) | 1 |
| | `seller_reviews_external` | 1 |
| Bronze, extractor | `orders_live` | 2 |
| | `order_items_live` (by order) | 12 |
| | `customer_shipping_live`, `shipping_details_live`, `review_live`, `product_reviews_live` | 1 each |
| Clickstream | `clickstream_external` | 2 |
| Warehouse | `orders_month`, `orders_plain` | 2 each |
| | `order_items_month_pc` (by order) | 12 |
| | `customer_shipping`, `shipping_details`, `review`, `product_reviews` | 1 each |
| Silver (views, real identifier today) | `stg_orders`, `stg_clickstream` | 2 each |
| | `int_order_items` | 6 |
| | `int_orders`, `stg_customer_shipping`, `int_buyer_country`, `stg_review` | 1 each |
| Gold | `fct_order_items` (lines of the person's orders) | **6** |

Tables at 0: `cart_external`, `returns_external`, `review_images_external`,
`seller_external`, `seller_products_external`, `subscription_external`,
`wishlist_item_external`.

The same script with a made-up value returned 42 counts, all 0 (10:20:58).

## Dry run on the bronze files

`ingestion/erase_subject.py`, no `--apply`, on `gs://data-engineering-i1-g04/bronze`:
09:53:13 to 09:54:39, **82.0 s**, 158 MiB read.

| Table | Rows read | Rows of the person | Files |
|---|---|---|---|
| `buyer` | 100,000 | 1 | 1 |
| `orders` | 672,520 | 6 | 3: export 2, extractor 2, `_incremental` 2 |
| `review` | 222,644 | 2 | 2 (export, extractor) |
| `clickstream` | 37,210 | 2 | 1 |
| `customer` | 130,766 | 1 | 1 |
| `customer_shipping` | 400,002 | 2 | 2 |
| `customer_payment` | 100,000 | 1 | 1 |
| `seller_reviews` | 111,322 | 1 | 1 |
| `order_items` | 824,300 | 24 | 2 (12 each) |
| `shipment` | 408,560 | 12 | 1 |
| `payment` | 222,644 | 2 | 1 |
| `shipping_details` | 400,002 | 2 | 2 |
| `payment_details` | 100,000 | 1 | 1 |
| `product_reviews` | 222,644 | 2 | 2 |
| Other tables and the dead letter queue (7 rows read) | | 0 | 0 |

**59 rows in 21 files.** Keys found: 2 `order_id`, 1 `address_id`, 1 `payment_id`,
1 `review_id`.

### The two counts agree, except for one file

Table by table, the file counts equal the BigQuery counts. One difference:
`bronze/postgres/_incremental/orders/part-20261106T084916524417.parquet` holds 2
rows of subject A (of 223,259). No external table reads that folder
(`orders_live` reads `postgres/orders/*`), so BigQuery cannot see them. Only a read
of the files finds them.

## Gold keeps the person's purchases

Gold has no identifier. It still holds 6 order lines whose `order_id` belongs to
subject A's orders, until gold is rebuilt: they are linked to the person only by
the key.

## The rewrite, on a copy

| Step | Start | End | Duration |
|---|---|---|---|
| Copy the 21 files to `test-erasure/` | 10:10:05 | 10:11:51 | 102.9 s |
| Rewrite and count again (`--apply`, no `--production`) | 10:12:14 | 10:14:40 | 141.4 s (the script) |
| Delete `test-erasure/` | 10:17:14 | 10:17:23 | 9.3 s |

The copy was 21 objects, 124,996,566 bytes, the exact sum of the sources. Rows
removed from the copy, and rows left (the final count is 0 in all 22 tables):

| Table | Rows before | Removed | Rows after |
|---|---|---|---|
| `orders` (3 files) | 371,633 | 6 | 371,627 |
| `order_items` (2) | 824,300 | 24 | 824,276 |
| `shipment` | 408,560 | 12 | 408,548 |
| `payment` | 222,644 | 2 | 222,642 |
| `review` (2) | 222,644 | 2 | 222,642 |
| `product_reviews` (2) | 222,644 | 2 | 222,642 |
| `customer_shipping` (2) | 400,002 | 2 | 400,000 |
| `shipping_details` (2) | 400,002 | 2 | 400,000 |
| `customer` | 130,766 | 1 | 130,765 |
| `buyer` | 100,000 | 1 | 99,999 |
| `customer_payment` | 100,000 | 1 | 99,999 |
| `payment_details` | 100,000 | 1 | 99,999 |
| `seller_reviews` | 111,322 | 1 | 111,321 |
| `clickstream` | 200 | 2 | 198 |

The script reads each rewritten file back and checks that no row of the person is
left and that the row count fell by the exact number removed. It did not stop. The
21 objects weigh 125,023,046 bytes after the rewrite, 26,480 more than before: the
rows removed do not make the files smaller, the internal layout differs.

The script was also tested on synthetic files before this: dry run, rewrite,
the refusal to write on the production prefix without `--production`, and the
refusal of a short identifier.

## What survives, checked after the deletion

At 10:17 `test-erasure/` held no live object and **42 soft-deleted versions**:

- 21 are the copies with subject A, replaced by the rewrite: soft-deleted 10:12:24
  to 10:14:21, 124,996,566 bytes, deleted for good 27 November 10:12:24 to 10:14:21;
- 21 are the rewritten files, removed by the deletion: soft-deleted 10:17:20 to
  10:17:21, 125,023,046 bytes, deleted for good 27 November 10:17:20 to 10:17:21.

Together 250,019,612 bytes, deleted for good between **27 November 10:12:24 and
10:17:21 UTC**, 7 days after (`hard_delete_time`, `gcloud storage objects describe
--soft-deleted`). The bucket's policy is 604,800 s. These test
copies hold whole tables of real (synthetic) data, not one person, so they stay
recoverable for 7 days like the files of bronze.

No way to purge them early was found: `gcloud storage rm` has no option for
soft-deleted objects, and `gcloud storage buckets update --clear-soft-delete` says
it "does not affect objects already in soft-deleted state". Not tested.

`bronze/` was not written to: the script refuses `--apply` on it without
`--production`, and 279 Parquet files were counted there after the deletion.

## The identifier in the job history

Run with a made-up value as the query parameter (10:20:58): the value is not in
`INFORMATION_SCHEMA.JOBS` (0 of 1 job, user and project), but it is in the job's
configuration read with `bq show -j`. A query parameter hides the value better than
text, not completely.

## What was not tested

- **An erasure on production**, and the rebuild of gold after one. The build of
  gold itself ran on a test target on 19 November 2026 (39.57 s,
  [pseudonymisation evidence](pii-redaction-test.md)).
- **The warehouse `DELETE`.** The counts ran; the statements did not.
- **Pausing the nightly DAG and stopping the consumer.**
- **Silver with the hash.** The hashed tables are not in production yet, so silver
  was counted with the real identifier, in the views.
- **That the source restores the person.** It follows from the code of the
  extractor ("each run bronze matches the source") and was not run: the extractor
  was not started.
- **Free text.** Only the identifier was searched.
