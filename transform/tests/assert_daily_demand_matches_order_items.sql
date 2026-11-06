-- The aggregate must add up to the lines it comes from.

SELECT *
FROM (
    SELECT SUM(qty) AS units, SUM(line_revenue) AS revenue
    FROM {{ ref('fct_order_items') }}
) AS lines
CROSS JOIN (
    SELECT SUM(units_sold) AS units_sold, SUM(gross_revenue) AS gross_revenue
    FROM {{ ref('fct_daily_demand') }}
) AS demand
WHERE lines.units != demand.units_sold
    OR lines.revenue != demand.gross_revenue
