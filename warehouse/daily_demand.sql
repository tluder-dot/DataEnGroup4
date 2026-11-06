-- Step 4, N3: the daily demand materialised view, and the collapse ratio.
-- Run in the BigQuery console, location europe-west1.

-- The view the ML team reads from. Grain: product x country x order date.
-- The country is the buyer's default shipping address (docs/model/star-daily-demand.md).
-- It reads order_items_month_pc, the tuned copy, and joins three small tables:
-- BigQuery accepted the three joins when the view was created on 5 November 2026.
CREATE MATERIALIZED VIEW `data-engineering-i1.g04_warehouse.daily_demand_country_mv`
OPTIONS (enable_refresh = TRUE, refresh_interval_minutes = 30) AS
SELECT
  oi.p_id,
  sd.country,
  oi.order_date,
  SUM(oi.qty) AS units,
  SUM(oi.qty * oi.price_at_purchase) AS revenue
FROM `data-engineering-i1.g04_warehouse.order_items_month_pc` AS oi
JOIN `data-engineering-i1.g04_warehouse.orders_plain` AS o USING (order_id)
JOIN `data-engineering-i1.g04_warehouse.customer_shipping` AS cs
  ON cs.c_id = o.buyer_id AND cs.is_default = '1'
JOIN `data-engineering-i1.g04_warehouse.shipping_details` AS sd
  ON sd.address_id = cs.address_id
GROUP BY oi.p_id, sd.country, oi.order_date;

-- The course's version (product x day, no country, one table): the one whose
-- collapse ratio the lesson checks.
CREATE MATERIALIZED VIEW `data-engineering-i1.g04_warehouse.daily_demand_mv`
OPTIONS (enable_refresh = TRUE, refresh_interval_minutes = 30) AS
SELECT
  p_id,
  order_date,
  SUM(qty) AS units,
  SUM(qty * price_at_purchase) AS revenue
FROM `data-engineering-i1.g04_warehouse.order_items_month_pc`
GROUP BY p_id, order_date;

-- A coarser grain, to show the ratio can move: product x month.
CREATE MATERIALIZED VIEW `data-engineering-i1.g04_warehouse.monthly_demand_mv`
OPTIONS (enable_refresh = TRUE, refresh_interval_minutes = 30) AS
SELECT
  p_id,
  DATE_TRUNC(order_date, MONTH) AS month,
  SUM(qty) AS units,
  SUM(qty * price_at_purchase) AS revenue
FROM `data-engineering-i1.g04_warehouse.order_items_month_pc`
GROUP BY p_id, month;

-- Collapse ratio = fact rows / distinct groups. Near 1.00 = the view saves no bytes.
WITH f AS (
  SELECT oi.p_id, oi.order_date, sd.country
  FROM `data-engineering-i1.g04_warehouse.order_items_month_pc` AS oi
  JOIN `data-engineering-i1.g04_warehouse.orders_plain` AS o USING (order_id)
  JOIN `data-engineering-i1.g04_warehouse.customer_shipping` AS cs
    ON cs.c_id = o.buyer_id AND cs.is_default = '1'
  JOIN `data-engineering-i1.g04_warehouse.shipping_details` AS sd
    ON sd.address_id = cs.address_id
)
SELECT
  COUNT(*) AS order_lines,
  COUNT(DISTINCT FORMAT('%s|%t', p_id, order_date)) AS product_day,
  COUNT(DISTINCT FORMAT('%s|%t|%s', p_id, order_date, country)) AS product_country_day,
  COUNT(DISTINCT FORMAT('%s|%t', p_id, DATE_TRUNC(order_date, MONTH))) AS product_month,
  COUNT(DISTINCT p_id) AS product
FROM f;
