-- Count one person's rows in every layer, without changing anything.
-- Part of docs/runbooks/erasure.md. The identifier is a query parameter, so it
-- is never in the text of the query, which the job history shows to the whole
-- project. Run it with:
--   bq --location=europe-west1 query --nouse_legacy_sql --use_cache=false ^
--      --parameter="subject::%SUBJECT_ID%" < docs/runbooks/erasure-counts.sql
-- Every count is a number of rows, never a value.
--
-- Silver: today the views hold the real identifier. Once the hashed buyer ID is
-- deployed (transform/macros/pseudonymise.sql), stg_orders and
-- stg_customer_shipping hold the hash, and stg_review and stg_clickstream have
-- no buyer_id any more. Then count the two tables with the hash
--   TO_HEX(SHA256(CONCAT((SELECT salt FROM g04_secrets.pii_salt), sid)))
-- and delete the stg_review and stg_clickstream lines.
DECLARE sid STRING DEFAULT @subject;
CREATE TEMP TABLE oids AS SELECT order_id FROM `data-engineering-i1.g04_bronze_1.orders_external` WHERE buyer_id = sid UNION DISTINCT SELECT order_id FROM `data-engineering-i1.g04_bronze_1.orders_live` WHERE buyer_id = sid;
CREATE TEMP TABLE aids AS SELECT address_id FROM `data-engineering-i1.g04_bronze_1.customer_shipping_external` WHERE c_id = sid UNION DISTINCT SELECT address_id FROM `data-engineering-i1.g04_bronze_1.customer_shipping_live` WHERE c_id = sid;
CREATE TEMP TABLE pids AS SELECT payment_id FROM `data-engineering-i1.g04_bronze_1.customer_payment_external` WHERE c_id = sid;
CREATE TEMP TABLE rids AS SELECT review_id FROM `data-engineering-i1.g04_bronze_1.review_external` WHERE buyer_id = sid UNION DISTINCT SELECT review_id FROM `data-engineering-i1.g04_bronze_1.review_live` WHERE buyer_id = sid;
SELECT layer, tbl, n FROM (SELECT 'bronze export' AS layer, 'buyer_external' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_bronze_1.buyer_external` WHERE buyer_id = sid
UNION ALL
SELECT 'bronze export' AS layer, 'orders_external' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_bronze_1.orders_external` WHERE buyer_id = sid
UNION ALL
SELECT 'bronze export' AS layer, 'cart_external' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_bronze_1.cart_external` WHERE buyer_id = sid
UNION ALL
SELECT 'bronze export' AS layer, 'returns_external' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_bronze_1.returns_external` WHERE buyer_id = sid
UNION ALL
SELECT 'bronze export' AS layer, 'review_external' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_bronze_1.review_external` WHERE buyer_id = sid
UNION ALL
SELECT 'bronze export' AS layer, 'wishlist_item_external' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_bronze_1.wishlist_item_external` WHERE buyer_id = sid
UNION ALL
SELECT 'bronze export' AS layer, 'customer_external' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_bronze_1.customer_external` WHERE c_id = sid
UNION ALL
SELECT 'bronze export' AS layer, 'customer_shipping_external' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_bronze_1.customer_shipping_external` WHERE c_id = sid
UNION ALL
SELECT 'bronze export' AS layer, 'customer_payment_external' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_bronze_1.customer_payment_external` WHERE c_id = sid
UNION ALL
SELECT 'bronze export' AS layer, 'subscription_external' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_bronze_1.subscription_external` WHERE c_id = sid
UNION ALL
SELECT 'bronze export' AS layer, 'seller_external' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_bronze_1.seller_external` WHERE seller_id = sid
UNION ALL
SELECT 'bronze export' AS layer, 'seller_products_external' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_bronze_1.seller_products_external` WHERE seller_id = sid
UNION ALL
SELECT 'bronze export' AS layer, 'seller_reviews_external' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_bronze_1.seller_reviews_external` WHERE seller_id = sid OR review_id IN (SELECT review_id FROM rids)
UNION ALL
SELECT 'bronze export' AS layer, 'order_items_external (by order)' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_bronze_1.order_items_external` WHERE order_id IN (SELECT order_id FROM oids)
UNION ALL
SELECT 'bronze export' AS layer, 'payment_external (by order)' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_bronze_1.payment_external` WHERE order_id IN (SELECT order_id FROM oids)
UNION ALL
SELECT 'bronze export' AS layer, 'shipment_external (by order)' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_bronze_1.shipment_external` WHERE order_id IN (SELECT order_id FROM oids)
UNION ALL
SELECT 'bronze export' AS layer, 'shipping_details_external (by address)' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_bronze_1.shipping_details_external` WHERE address_id IN (SELECT address_id FROM aids)
UNION ALL
SELECT 'bronze export' AS layer, 'payment_details_external (by payment)' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_bronze_1.payment_details_external` WHERE payment_id IN (SELECT payment_id FROM pids)
UNION ALL
SELECT 'bronze export' AS layer, 'review_images_external (by review)' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_bronze_1.review_images_external` WHERE review_id IN (SELECT review_id FROM rids)
UNION ALL
SELECT 'bronze export' AS layer, 'product_reviews_external (by review)' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_bronze_1.product_reviews_external` WHERE review_id IN (SELECT review_id FROM rids)
UNION ALL
SELECT 'bronze extractor' AS layer, 'orders_live' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_bronze_1.orders_live` WHERE buyer_id = sid
UNION ALL
SELECT 'bronze extractor' AS layer, 'review_live' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_bronze_1.review_live` WHERE buyer_id = sid
UNION ALL
SELECT 'bronze extractor' AS layer, 'customer_shipping_live' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_bronze_1.customer_shipping_live` WHERE c_id = sid
UNION ALL
SELECT 'bronze extractor' AS layer, 'order_items_live (by order)' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_bronze_1.order_items_live` WHERE order_id IN (SELECT order_id FROM oids)
UNION ALL
SELECT 'bronze extractor' AS layer, 'shipping_details_live (by address)' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_bronze_1.shipping_details_live` WHERE address_id IN (SELECT address_id FROM aids)
UNION ALL
SELECT 'bronze extractor' AS layer, 'product_reviews_live (by review)' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_bronze_1.product_reviews_live` WHERE review_id IN (SELECT review_id FROM rids)
UNION ALL
SELECT 'clickstream' AS layer, 'clickstream_external' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_bronze_1.clickstream_external` WHERE buyer_id = sid
UNION ALL
SELECT 'warehouse' AS layer, 'orders_month' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_warehouse.orders_month` WHERE buyer_id = sid
UNION ALL
SELECT 'warehouse' AS layer, 'orders_plain' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_warehouse.orders_plain` WHERE buyer_id = sid
UNION ALL
SELECT 'warehouse' AS layer, 'review' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_warehouse.review` WHERE buyer_id = sid
UNION ALL
SELECT 'warehouse' AS layer, 'customer_shipping' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_warehouse.customer_shipping` WHERE c_id = sid
UNION ALL
SELECT 'warehouse' AS layer, 'order_items_month_pc (by order)' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_warehouse.order_items_month_pc` WHERE order_id IN (SELECT order_id FROM oids)
UNION ALL
SELECT 'warehouse' AS layer, 'shipping_details (by address)' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_warehouse.shipping_details` WHERE address_id IN (SELECT address_id FROM aids)
UNION ALL
SELECT 'warehouse' AS layer, 'product_reviews (by review)' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_warehouse.product_reviews` WHERE review_id IN (SELECT review_id FROM rids)
UNION ALL
SELECT 'silver (view, real ID today)' AS layer, 'stg_orders' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_silver.stg_orders` WHERE buyer_id = sid
UNION ALL
SELECT 'silver (view, real ID today)' AS layer, 'int_orders' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_silver.int_orders` WHERE buyer_id = sid
UNION ALL
SELECT 'silver (view, real ID today)' AS layer, 'int_order_items' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_silver.int_order_items` WHERE buyer_id = sid
UNION ALL
SELECT 'silver (view, real ID today)' AS layer, 'stg_customer_shipping' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_silver.stg_customer_shipping` WHERE buyer_id = sid
UNION ALL
SELECT 'silver (view, real ID today)' AS layer, 'int_buyer_country' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_silver.int_buyer_country` WHERE buyer_id = sid
UNION ALL
SELECT 'silver (view, real ID today)' AS layer, 'stg_review' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_silver.stg_review` WHERE buyer_id = sid
UNION ALL
SELECT 'silver (view, real ID today)' AS layer, 'stg_clickstream' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_silver.stg_clickstream` WHERE buyer_id = sid
UNION ALL
SELECT 'gold (no identifier)' AS layer, 'fct_order_items (lines of the person orders)' AS tbl, COUNT(*) AS n FROM `data-engineering-i1.g04_gold.fct_order_items` WHERE order_id IN (SELECT order_id FROM oids)) ORDER BY layer, tbl;
