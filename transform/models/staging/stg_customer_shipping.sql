-- One row per address of a customer: a buyer has 1 to 3.
-- Renames c_id to buyer_id, the name orders uses for the same person (trap 11).
-- Casts is_default from the text '0' and '1' to a boolean.
-- Replaces the buyer ID by its salted hash, the same one stg_orders gives, so
-- the two still join. A table, not a view (ADR 0010).

{{ config(materialized='table') }}

SELECT
    address_id,
    {{ pseudonymise('c_id') }} AS buyer_id,
    is_default = '1' AS is_default
FROM {{ source('marketplace', 'customer_shipping') }}
