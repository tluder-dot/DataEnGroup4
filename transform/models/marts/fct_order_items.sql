{{ config(
    partition_by={'field': 'order_date', 'data_type': 'date', 'granularity': 'month'},
    cluster_by=['p_id']
) }}

-- GRAIN: one product in one real order. Partitioned by month and clustered on
-- p_id, the shape docs/warehouse-tuning.md measured. buyer_id stays in silver:
-- gold holds no identifier of a person.

SELECT
    i.order_id,
    i.p_id,
    b.country,
    i.order_date,
    i.qty,
    i.price_at_purchase,
    i.qty * i.price_at_purchase AS line_revenue
FROM {{ ref('int_order_items') }} AS i
LEFT JOIN {{ ref('int_buyer_country') }} AS b USING (buyer_id)
