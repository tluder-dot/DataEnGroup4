-- One row per reviewed product. A product has up to 376 reviews and no rule
-- picks one, so joining reviews to order lines multiplies them 17.30 times.
-- The fix is to aggregate first, then join one to one.

SELECT
    pr.p_id,
    COUNT(*) AS n_reviews,
    ROUND(AVG(r.rating), 3) AS avg_rating,
    COUNTIF(r.rating > 4) > 0 AS has_rating_above_four
FROM {{ ref('stg_product_reviews') }} AS pr
JOIN {{ ref('stg_review') }} AS r USING (review_id)
GROUP BY pr.p_id
