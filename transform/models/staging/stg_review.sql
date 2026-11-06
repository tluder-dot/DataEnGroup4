-- One row per review.
-- Turns blank text into NULL: 14 empty r_desc and 110 of a single space (trap 5).
-- Keeps the strings None, NA, N/A and NULL (trap 4): a reviewer can type them,
-- and nothing tells them from a missing value.
-- Drops csv_index (trap 1) and seller_product_flag, always S (trap 9).

SELECT
    review_id,
    buyer_id,
    NULLIF(TRIM(r_desc), '') AS review_text,
    NULLIF(TRIM(title), '') AS review_title,
    rating
FROM {{ source('marketplace', 'review') }}
