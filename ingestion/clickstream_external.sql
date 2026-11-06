-- The clickstream as an external table in bronze.
--
-- Columns are declared because no file holds them all: a batch without an
-- order has no order_id, amount or items, and BigQuery would take its column
-- list from one such file and silently lose the rest.
-- enable_list_inference reads items as an array of structs.

CREATE OR REPLACE EXTERNAL TABLE `data-engineering-i1.g04_bronze_1.clickstream_external` (
  schema_version INT64,
  event_id STRING,
  event_type STRING,
  event_time STRING,
  emitted_at STRING,
  session_id STRING,
  buyer_id STRING,
  p_id STRING,
  price FLOAT64,
  qty FLOAT64,
  order_id FLOAT64,
  payment_method STRING,
  amount FLOAT64,
  currency STRING,
  items ARRAY<STRUCT<p_id STRING, qty INT64, price FLOAT64>>
)
WITH PARTITION COLUMNS (dt DATE)
OPTIONS (
  uris = ['gs://data-engineering-i1-g04/bronze/clickstream/*'],
  format = 'PARQUET',
  enable_list_inference = TRUE,
  hive_partition_uri_prefix = 'gs://data-engineering-i1-g04/bronze/clickstream'
);
