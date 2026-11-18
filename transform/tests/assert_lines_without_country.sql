{{ config(severity='warn') }}

-- A warning, not an error: new customers sign up without an address, so their
-- orders have no country. They stay in gold under 'Unknown', and this counts them.

SELECT
    order_id,
    p_id
FROM {{ ref('fct_order_items') }}
WHERE country = 'Unknown'
