{{ config(
    partition_by={'field': 'order_date', 'data_type': 'date', 'granularity': 'month'},
    cluster_by=['p_id']
) }}

-- GRAIN: one product in one real order. Partitioned by month and clustered on
-- p_id, the shape docs/warehouse-tuning.md measured. buyer_id stays in silver:
-- gold holds no identifier of a person.
-- A buyer who signed up without an address has no country: their lines count
-- under 'Unknown' rather than vanish (assert_lines_without_country warns).

SELECT
    i.order_id,
    i.p_id,
    COALESCE(b.country, 'Unknown') AS country,
    i.order_date,
    i.qty,
    i.price_at_purchase,
    i.qty * i.price_at_purchase AS line_revenue
FROM {{ ref('int_order_items') }} AS i
LEFT JOIN {{ ref('int_buyer_country') }} AS b USING (buyer_id)
