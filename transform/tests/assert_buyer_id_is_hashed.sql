-- The real buyer ID must not reach silver. A hashed ID is 64 lowercase hex
-- characters; anything else is a row that skipped pseudonymise().

SELECT buyer_id
FROM {{ ref('stg_orders') }}
WHERE NOT REGEXP_CONTAINS(buyer_id, r'^[0-9a-f]{64}$')

UNION ALL

SELECT buyer_id
FROM {{ ref('stg_customer_shipping') }}
WHERE NOT REGEXP_CONTAINS(buyer_id, r'^[0-9a-f]{64}$')
