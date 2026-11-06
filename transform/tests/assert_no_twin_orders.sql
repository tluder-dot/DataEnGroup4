-- Revenue not double-counted. The grain test cannot see a twin: it has another
-- order_id, so it passes with every order in twice. This test looks for what
-- makes a twin: the same buyer, card and lines as an order up to 4 days earlier.

WITH orders AS (
    SELECT
        order_id,
        buyer_id,
        payment_id,
        order_date,
        TO_JSON_STRING(ARRAY_AGG(STRUCT(p_id, qty, price_at_purchase) ORDER BY p_id)) AS order_lines
    FROM {{ ref('int_order_items') }}
    GROUP BY order_id, buyer_id, payment_id, order_date
),

with_previous AS (
    SELECT
        *,
        LAG(order_date) OVER (
            PARTITION BY buyer_id, payment_id, order_lines
            ORDER BY order_date, order_id
        ) AS previous_identical_order_date
    FROM orders
)

SELECT order_id
FROM with_previous
WHERE DATE_DIFF(order_date, previous_identical_order_date, DAY) <= {{ var('twin_window_days', 4) }}
