-- Daily revenue report: the seven latest days in gold, newest first.
-- Revenue has one definition: line_revenue in fct_order_items, qty times
-- price_at_purchase, with the duplicate orders already removed.
-- The shop runs on a simulated clock, so "latest" is the newest day in the
-- data, not yesterday's date, and the newest day may still be filling up.
SELECT
    order_date,
    COUNT(DISTINCT order_id) AS orders,
    SUM(qty) AS units,
    ROUND(SUM(line_revenue), 2) AS revenue_eur
FROM `data-engineering-i1.g04_gold.fct_order_items`
GROUP BY order_date
ORDER BY order_date DESC
LIMIT 7;
