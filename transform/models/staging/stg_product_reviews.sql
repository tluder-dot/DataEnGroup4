-- Bridge: which review is about which product. A product has many reviews, so
-- joining this to order lines multiplies them: use int_product_ratings.

SELECT
    p_id,
    review_id
FROM {{ source('marketplace', 'product_reviews') }}
