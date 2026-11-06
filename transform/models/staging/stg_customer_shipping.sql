-- One row per address of a customer: a buyer has 1 to 3.
-- Renames c_id to buyer_id, the name orders uses for the same person (trap 11).
-- Casts is_default from the text '0' and '1' to a boolean.
-- Drops csv_index (trap 1).

SELECT
    address_id,
    c_id AS buyer_id,
    is_default = '1' AS is_default
FROM {{ source('marketplace', 'customer_shipping') }}
