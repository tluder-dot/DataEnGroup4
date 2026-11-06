-- GRAIN: one calendar day, from the first order to the last, days without an
-- order included.

SELECT
    order_date,
    EXTRACT(YEAR FROM order_date) AS year,
    EXTRACT(QUARTER FROM order_date) AS quarter,
    EXTRACT(MONTH FROM order_date) AS month,
    EXTRACT(ISOWEEK FROM order_date) AS iso_week,
    FORMAT_DATE('%A', order_date) AS day_of_week,
    EXTRACT(DAYOFWEEK FROM order_date) IN (1, 7) AS is_weekend
FROM UNNEST(GENERATE_DATE_ARRAY(
    (SELECT MIN(order_date) FROM {{ ref('int_orders') }}),
    (SELECT MAX(order_date) FROM {{ ref('int_orders') }})
)) AS order_date
