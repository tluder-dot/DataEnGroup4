-- GRAIN: one country a buyer lives in, plus 'Unknown' for buyers who gave no
-- address.

SELECT
    c.country,
    c.country_code,
    COUNT(b.buyer_id) AS n_buyers
FROM {{ ref('country_codes') }} AS c
LEFT JOIN {{ ref('int_buyer_country') }} AS b USING (country)
GROUP BY c.country, c.country_code
