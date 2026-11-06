-- An order line is dated by its order. The inner join is what removes the
-- twins' lines: only lines of a real order survive.

SELECT
    i.order_id,
    i.p_id,
    i.qty,
    i.price_at_purchase,
    o.buyer_id,
    o.payment_id,
    o.order_date
FROM {{ ref('stg_order_items') }} AS i
JOIN {{ ref('int_orders') }} AS o USING (order_id)
