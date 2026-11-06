{{ config(
    partition_by={'field': 'order_date', 'data_type': 'date', 'granularity': 'month'},
    cluster_by=['p_id', 'country']
) }}

-- GRAIN: one product, one country, one day, where at least one unit was
-- ordered. A missing row means zero units. order_count sums across days and
-- countries, not across products: an order of two products counts in both.

SELECT
    {{ dbt_utils.generate_surrogate_key(['p_id', 'country', 'order_date']) }} AS demand_key,
    p_id,
    country,
    order_date,
    SUM(qty) AS units_sold,
    SUM(line_revenue) AS gross_revenue,
    COUNT(DISTINCT order_id) AS order_count
FROM {{ ref('fct_order_items') }}
GROUP BY p_id, country, order_date
