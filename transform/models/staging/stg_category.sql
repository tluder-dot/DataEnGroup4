-- One row per category. Renames name, which says nothing once joined.
-- Drops csv_index (trap 1) and c_desc, which no model reads.

SELECT
    category_id,
    name AS category_name
FROM {{ source('marketplace', 'category') }}
