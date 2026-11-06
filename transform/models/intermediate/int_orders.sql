-- One row per real order: this is the company's rule for twin orders (trap 6).
-- Every order in the history was loaded twice. A twin has the same buyer, card
-- and lines as an earlier order, placed 0 to 4 days later, so DISTINCT cannot
-- see it. An order is kept unless such an earlier order exists.
--
-- Measured on the export: removes 111,326 of 222,644 orders. All 111,322 real
-- twins go, and so do 4 genuine repeat orders that look exactly like a twin.

WITH line_signatures AS (
    SELECT
        order_id,
        TO_JSON_STRING(ARRAY_AGG(STRUCT(p_id, qty, price_at_purchase) ORDER BY p_id)) AS order_lines
    FROM {{ ref('stg_order_items') }}
    GROUP BY order_id
),

with_previous AS (
    SELECT
        o.order_id,
        o.buyer_id,
        o.payment_id,
        o.order_date,
        s.order_lines,
        LAG(o.order_date) OVER (
            PARTITION BY o.buyer_id, o.payment_id, s.order_lines
            ORDER BY o.order_date, o.order_id
        ) AS previous_identical_order_date
    FROM {{ ref('stg_orders') }} AS o
    LEFT JOIN line_signatures AS s USING (order_id)
)

SELECT
    order_id,
    buyer_id,
    payment_id,
    order_date
FROM with_previous
WHERE order_lines IS NULL
    OR previous_identical_order_date IS NULL
    OR DATE_DIFF(order_date, previous_identical_order_date, DAY) > {{ var('twin_window_days', 4) }}
