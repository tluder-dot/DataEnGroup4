-- GRAIN: one product. A product without reviews has 0 reviews, not NULL: zero
-- is a fact. Reviews arrive already aggregated, so the join cannot fan out.

SELECT
    p.p_id,
    p.product_name,
    c.category_name,
    p.price,
    COALESCE(r.n_reviews, 0) AS n_reviews,
    r.avg_rating,
    COALESCE(r.has_rating_above_four, FALSE) AS has_rating_above_four
FROM {{ ref('stg_product') }} AS p
LEFT JOIN {{ ref('stg_category') }} AS c USING (category_id)
LEFT JOIN {{ ref('int_product_ratings') }} AS r USING (p_id)
