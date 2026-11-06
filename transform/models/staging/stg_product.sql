-- One row per product.
-- Turns blank names into NULL: 6 empty strings (trap 5).
-- Rounds price to cents, removing the float noise of 35,205 prices (trap 7).
-- Drops csv_index (trap 1) and p_desc, which no model reads.

SELECT
    p_id,
    NULLIF(TRIM(p_name), '') AS product_name,
    CAST(ROUND(price, 2) AS NUMERIC) AS price,
    qty AS stock_qty,
    category_id
FROM {{ source('marketplace', 'product') }}
