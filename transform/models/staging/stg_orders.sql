-- One row per order row in bronze. The twins are still here: recognising one
-- needs its order lines, so int_orders removes them (trap 6).
-- Drops csv_index, the export's row number, on all 222,644 rows (trap 1).
-- Drops discount_id, empty on every row (trap 8).

SELECT
    order_id,
    buyer_id,
    payment_id,
    order_date
FROM {{ source('marketplace', 'orders') }}
