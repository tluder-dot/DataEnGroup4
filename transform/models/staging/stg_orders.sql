-- One row per order row in bronze. The twins are still here: recognising one
-- needs its order lines, so int_orders removes them (trap 6).
-- Drops discount_id, empty on every row (trap 8).
-- Replaces buyer_id by its salted hash: no model after this one sees the real
-- identifier. A table, not a view, so that a reader of silver never needs the
-- salt (ADR 0010).

{{ config(materialized='table') }}

SELECT
    order_id,
    {{ pseudonymise('buyer_id') }} AS buyer_id,
    payment_id,
    order_date
FROM {{ source('marketplace', 'orders') }}
