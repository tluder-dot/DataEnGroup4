-- One row per category. Renames name, which says nothing once joined.
-- Drops csv_index, the export's row number (trap 1), and c_desc, which no
-- model reads. The only source still read from the export.

SELECT
    category_id,
    name AS category_name
FROM {{ source('marketplace', 'category') }}
