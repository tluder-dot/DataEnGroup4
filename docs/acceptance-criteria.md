# Acceptance criteria

What the business can rely on in gold, each with the test that proves it. A
criterion without a test is a hope. Results from `dbt build` and
`dbt source freshness` on 6 November 2026: PASS=79, WARN=2, ERROR=0.

| Criterion | Test | Result |
|---|---|---|
| Revenue is not double-counted: no order is in twice | [`assert_no_twin_orders`](../transform/tests/assert_no_twin_orders.sql) | Pass. With the twins put back: FAIL 111,326, and gold is skipped |
| The rule tells a twin from a repeat order | [`twin_is_removed_only_within_the_window`](../transform/models/intermediate/_intermediate.yml), a unit test | Pass |
| A fact has one row per grain | `unique_combination_of_columns` on [`fct_order_items` and `fct_daily_demand`](../transform/models/marts/_marts.yml) | Pass. With reviews joined to the lines: FAIL, and `fct_daily_demand` is skipped |
| Daily demand adds up to the order lines | [`assert_daily_demand_matches_order_items`](../transform/tests/assert_daily_demand_matches_order_items.sql) | Pass |
| Every order line has a product | `relationships` to `dim_product` | Pass |
| Every order line has a country | `not_null` and `relationships` to `dim_country` | Pass |
| Every day of an order is in the calendar | `relationships` to `dim_date` | Pass |
| A buyer has one country | `unique` on [`int_buyer_country.buyer_id`](../transform/models/intermediate/_intermediate.yml) | Pass |
| Ratings are between 1 and 5 | `accepted_range` on [`stg_review.rating`](../transform/models/staging/_staging.yml) | Pass |
| A clickstream event counts once | `unique` on `stg_clickstream.event_id` | Pass |
| Every product has a name | `not_null` on `dim_product.product_name`, after trimming | **Warns: 6 products.** Their name is empty in the source, so gold shows NULL |
| No order line is free | [`assert_line_revenue_is_positive`](../transform/tests/assert_line_revenue_is_positive.sql) | **Warns: 15 lines.** 5 products cost under half a cent and round to 0.00 |
| Data is at most a day old | `dbt source freshness`, [thresholds with reasons](../transform/models/sources.yml) | **Fails today:** `orders` and `order_items` are stale, because nothing loads them nightly before step 7 |

**The grain test alone does not protect revenue.** With every twin back in gold,
it still passes: a twin has its own `order_id`. That is why
`assert_no_twin_orders` exists.

## Checked by hand, once

Against the course's figures for twins removed:

| Period | Course | Gold | Difference |
|---|---|---|---|
| 2025 | €6,495,841.28, 37,082 orders | €6,495,822.21, 37,080 orders | €19.07, 2 orders |
| 12 months to 2026-09-14 | €6,523,907.20, 37,147 orders | €6,523,867.58, 37,145 orders | €39.62, 2 orders |

Over the whole history, gold holds 111,318 orders, 693,316 units and
€19,599,891.62. Bronze as it arrived holds 222,644 orders and €39,199,900.62.

## What we could not test

- **4 genuine orders are removed.** A buyer who orders exactly the same thing on
  the same card within 4 days looks like a twin. Orders 48218, 89042, 109164 and
  110321 went this way, €58.69 of €19.6 M. Only the source's own generator can
  tell them apart, and using that would not work on a new order.
- **Revenue against the accounts.** No total from outside the platform exists
  to compare with. The figures above are the course's, compared once by hand.
- **The buyer's country at the time of the order.** Gold uses today's default
  address, so a buyer who moves takes their past orders along (star sketch, open
  questions).
- **Whether freshness sees a new file.** On an external table it reads when the
  table was recreated, so a loading job must recreate its table (step 7). The
  clickstream reads `emitted_at` instead.
