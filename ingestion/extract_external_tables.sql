-- The extractor's seven tables as external tables: <table>_live over
-- bronze/postgres/<table>/. dbt reads these.
--
-- Rerun it after every extraction, before dbt: freshness reads when a table
-- was last recreated, not when a file landed.
-- The export's <table>_external tables stay as they are: the warehouse reads
-- their csv_index and order_year.

CREATE OR REPLACE EXTERNAL TABLE `data-engineering-i1.g04_bronze_1.orders_live`
WITH PARTITION COLUMNS
OPTIONS (
  uris = ['gs://data-engineering-i1-g04/bronze/postgres/orders/*'],
  format = 'PARQUET',
  hive_partition_uri_prefix = 'gs://data-engineering-i1-g04/bronze/postgres/orders'
);

CREATE OR REPLACE EXTERNAL TABLE `data-engineering-i1.g04_bronze_1.order_items_live`
OPTIONS (uris = ['gs://data-engineering-i1-g04/bronze/postgres/order_items/*.parquet'], format = 'PARQUET');

CREATE OR REPLACE EXTERNAL TABLE `data-engineering-i1.g04_bronze_1.review_live`
OPTIONS (uris = ['gs://data-engineering-i1-g04/bronze/postgres/review/*.parquet'], format = 'PARQUET');

CREATE OR REPLACE EXTERNAL TABLE `data-engineering-i1.g04_bronze_1.product_reviews_live`
OPTIONS (uris = ['gs://data-engineering-i1-g04/bronze/postgres/product_reviews/*.parquet'], format = 'PARQUET');

CREATE OR REPLACE EXTERNAL TABLE `data-engineering-i1.g04_bronze_1.product_live`
OPTIONS (uris = ['gs://data-engineering-i1-g04/bronze/postgres/product/*.parquet'], format = 'PARQUET');

CREATE OR REPLACE EXTERNAL TABLE `data-engineering-i1.g04_bronze_1.customer_shipping_live`
OPTIONS (uris = ['gs://data-engineering-i1-g04/bronze/postgres/customer_shipping/*.parquet'], format = 'PARQUET');

CREATE OR REPLACE EXTERNAL TABLE `data-engineering-i1.g04_bronze_1.shipping_details_live`
OPTIONS (uris = ['gs://data-engineering-i1-g04/bronze/postgres/shipping_details/*.parquet'], format = 'PARQUET');
