-- Step 4, N2: the tuned variants, built from the untuned copies of 01_load_native_tables.sql.
-- Every variant exists so docs/warehouse-tuning.md can compare it, by dry run,
-- with the untuned table on the same query. Variants that bought nothing stay
-- on purpose: a step that saves nothing is a result.
-- Run in the BigQuery console, location europe-west1.

-- order_items, five layouts. Grain is the only thing that changes.
CREATE OR REPLACE TABLE `data-engineering-i1.g04_warehouse.order_items_clustered`
CLUSTER BY p_id AS
SELECT order_id, p_id, qty, price_at_purchase, order_date
FROM `data-engineering-i1.g04_warehouse.order_items_plain`;

CREATE OR REPLACE TABLE `data-engineering-i1.g04_warehouse.order_items_day`
PARTITION BY order_date
CLUSTER BY p_id AS
SELECT order_id, p_id, qty, price_at_purchase, order_date
FROM `data-engineering-i1.g04_warehouse.order_items_plain`;

CREATE OR REPLACE TABLE `data-engineering-i1.g04_warehouse.order_items_month`
PARTITION BY DATE_TRUNC(order_date, MONTH) AS
SELECT order_id, p_id, qty, price_at_purchase, order_date
FROM `data-engineering-i1.g04_warehouse.order_items_plain`;

CREATE OR REPLACE TABLE `data-engineering-i1.g04_warehouse.order_items_month_pc`
PARTITION BY DATE_TRUNC(order_date, MONTH)
CLUSTER BY p_id AS
SELECT order_id, p_id, qty, price_at_purchase, order_date
FROM `data-engineering-i1.g04_warehouse.order_items_plain`;

CREATE OR REPLACE TABLE `data-engineering-i1.g04_warehouse.order_items_year_pc`
PARTITION BY DATE_TRUNC(order_date, YEAR)
CLUSTER BY p_id AS
SELECT order_id, p_id, qty, price_at_purchase, order_date
FROM `data-engineering-i1.g04_warehouse.order_items_plain`;

-- orders by month
CREATE OR REPLACE TABLE `data-engineering-i1.g04_warehouse.orders_month`
PARTITION BY DATE_TRUNC(order_date, MONTH) AS
SELECT csv_index, order_id, buyer_id, discount_id, payment_id, order_date, order_year
FROM `data-engineering-i1.g04_warehouse.orders_plain`;

-- Q3 has no date: try the only levers left, clustering on the join and group keys.
CREATE OR REPLACE TABLE `data-engineering-i1.g04_warehouse.product_reviews_pc`
CLUSTER BY p_id AS
SELECT csv_index, p_id, review_id
FROM `data-engineering-i1.g04_warehouse.product_reviews`;

CREATE OR REPLACE TABLE `data-engineering-i1.g04_warehouse.review_c`
CLUSTER BY review_id AS
SELECT csv_index, review_id, buyer_id, r_desc, title, rating, seller_product_flag
FROM `data-engineering-i1.g04_warehouse.review`;
