-- Step 4, N1: the working set as native tables in g04_warehouse.
-- Source: the external tables in g04_bronze_1 (bronze stays in the bucket).
-- Columns are named, never SELECT *. Nothing is cleaned here: duplicates,
-- csv_index and the other defects are silver's job (L05).
-- Run in the BigQuery console, location europe-west1.

-- Untuned copies: the "before" of every measurement in docs/warehouse-tuning.md.
CREATE OR REPLACE TABLE `data-engineering-i1.g04_warehouse.orders_plain` AS
SELECT csv_index, order_id, buyer_id, discount_id, payment_id, order_date, order_year
FROM `data-engineering-i1.g04_bronze_1.orders_external`;

-- order_items has no date: it comes from orders through order_id.
CREATE OR REPLACE TABLE `data-engineering-i1.g04_warehouse.order_items_plain` AS
SELECT oi.order_id, oi.p_id, oi.qty, oi.price_at_purchase, o.order_date
FROM `data-engineering-i1.g04_bronze_1.order_items_external` AS oi
JOIN `data-engineering-i1.g04_bronze_1.orders_external` AS o USING (order_id);

-- The five tables that need no tuning: no date, read whole.
CREATE OR REPLACE TABLE `data-engineering-i1.g04_warehouse.review` AS
SELECT csv_index, review_id, buyer_id, r_desc, title, rating, seller_product_flag
FROM `data-engineering-i1.g04_bronze_1.review_external`;

CREATE OR REPLACE TABLE `data-engineering-i1.g04_warehouse.product_reviews` AS
SELECT csv_index, p_id, review_id
FROM `data-engineering-i1.g04_bronze_1.product_reviews_external`;

CREATE OR REPLACE TABLE `data-engineering-i1.g04_warehouse.product` AS
SELECT csv_index, p_id, p_name, p_desc, price, qty, category_id
FROM `data-engineering-i1.g04_bronze_1.product_external`;

CREATE OR REPLACE TABLE `data-engineering-i1.g04_warehouse.customer_shipping` AS
SELECT csv_index, address_id, c_id, is_default
FROM `data-engineering-i1.g04_bronze_1.customer_shipping_external`;

-- Only address_id and country: street, zip and phone are personal data that no
-- warehouse query needs (docs/data-dictionary.md), so they are not copied.
CREATE OR REPLACE TABLE `data-engineering-i1.g04_warehouse.shipping_details` AS
SELECT csv_index, address_id, country
FROM `data-engineering-i1.g04_bronze_1.shipping_details_external`;
