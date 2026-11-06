-- One row per buyer. An order carries no address and a buyer has 1 to 3, so
-- joining all of them doubles the orders (444,960 rows from 222,644). The data
-- has a rule that picks one: each buyer has exactly one default address.

SELECT
    cs.buyer_id,
    sd.country
FROM {{ ref('stg_customer_shipping') }} AS cs
JOIN {{ ref('stg_shipping_details') }} AS sd USING (address_id)
WHERE cs.is_default
