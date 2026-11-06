-- One row per product in an order.
-- Casts price_at_purchase from FLOAT64 to NUMERIC, so that revenue adds up to
-- the cent (trap 7).

SELECT
    order_id,
    p_id,
    qty,
    CAST(ROUND(price_at_purchase, 2) AS NUMERIC) AS price_at_purchase
FROM {{ source('marketplace', 'order_items') }}
