-- One row per address. Keeps the country only: street, city, zip and phone are
-- personal data that no model needs, and state holds regions (trap 11).
-- Drops csv_index (trap 1).

SELECT
    address_id,
    country
FROM {{ source('marketplace', 'shipping_details') }}
