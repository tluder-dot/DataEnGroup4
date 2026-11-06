-- GRAIN: one country a buyer lives in.

SELECT
    b.country,
    c.country_code,
    COUNT(*) AS n_buyers
FROM {{ ref('int_buyer_country') }} AS b
LEFT JOIN {{ ref('country_codes') }} AS c USING (country)
GROUP BY b.country, c.country_code
