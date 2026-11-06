# Lineage

Which model is built from which, read from dbt's `manifest.json` on 6 November
2026. To explore it, tests included: `dbt docs generate`, then
`dbt docs serve --port 8080 --host 0.0.0.0`
([how to run dbt](../transform/README.md)).

```mermaid
flowchart LR
  subgraph bronze["Bronze: sources and seed"]
    category
    clickstream
    country_codes
    customer_shipping
    order_items
    orders
    product
    product_reviews
    review
    shipping_details
  end
  subgraph staging["Silver: staging"]
    stg_category
    stg_clickstream
    stg_customer_shipping
    stg_order_items
    stg_orders
    stg_product
    stg_product_reviews
    stg_review
    stg_shipping_details
  end
  subgraph intermediate["Silver: intermediate"]
    int_buyer_country
    int_order_items
    int_orders
    int_product_ratings
  end
  subgraph marts["Gold"]
    dim_country
    dim_date
    dim_product
    fct_daily_demand
    fct_order_items
  end
  category --> stg_category
  clickstream --> stg_clickstream
  country_codes --> dim_country
  customer_shipping --> stg_customer_shipping
  fct_order_items --> fct_daily_demand
  int_buyer_country --> dim_country
  int_buyer_country --> fct_order_items
  int_order_items --> fct_order_items
  int_orders --> dim_date
  int_orders --> int_order_items
  int_product_ratings --> dim_product
  order_items --> stg_order_items
  orders --> stg_orders
  product --> stg_product
  product_reviews --> stg_product_reviews
  review --> stg_review
  shipping_details --> stg_shipping_details
  stg_category --> dim_product
  stg_customer_shipping --> int_buyer_country
  stg_order_items --> int_order_items
  stg_order_items --> int_orders
  stg_orders --> int_orders
  stg_product --> dim_product
  stg_product_reviews --> int_product_ratings
  stg_review --> int_product_ratings
  stg_shipping_details --> int_buyer_country
```

`category`, `customer_shipping` and the others on the left are bronze tables.
`clickstream` feeds `stg_clickstream` and nothing else yet: no gold model reads
it.

## If `orders`, the most upstream source, changes shape

`orders` reaches every fact: `stg_orders` → `int_orders` → `int_order_items` →
`fct_order_items` → `fct_daily_demand`, and `dim_date`, which is built from the
first and last order.

1. **A new column:** nothing breaks and nothing sees it. Staging names its
   columns, so add it to `stg_orders` if a model needs it.
2. **A dropped or renamed column:** `stg_orders` fails at the next build, and
   `dbt build` skips everything downstream. Gold keeps yesterday's data. Check
   the column list in `stg_orders` first, then the three columns the twin rule
   compares: `buyer_id`, `payment_id` and `order_date`.
3. **A changed type:** the most dangerous. If `order_date` became a timestamp,
   `DATE_DIFF` could still run and the rule still look fine. Run the unit test
   on `int_orders`, then `assert_no_twin_orders`.
4. **A new way of writing orders:** if an order could be corrected rather than
   duplicated, the twin rule's 4-day window needs a new look. No test catches
   that: compare gold's revenue with `payment` by hand.
