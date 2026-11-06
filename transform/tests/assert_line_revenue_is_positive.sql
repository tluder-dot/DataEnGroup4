{{ config(severity='warn') }}

-- A warning, not an error: 5 products cost under half a cent, so a line of them
-- rounds to 0.00. That is a catalogue problem, not a broken pipeline.

SELECT
    order_id,
    p_id,
    line_revenue
FROM {{ ref('fct_order_items') }}
WHERE line_revenue <= 0
