-- One row per event. The consumer delivers at least once, so a crash or a
-- rebalance writes some events twice (ADR 0003): keeps one copy of each.
-- An event is (event_id, emitted_at), not event_id alone: the storefront draws
-- event_id from a random generator seeded with TRAFFIC_SEED, so every restart
-- of the load generator reuses the same IDs for new events. On 12 November,
-- 9,085 of 19,138 rows in bronze reused an ID; keying on event_id alone
-- dropped them.
-- Casts the timestamps, and qty and order_id, which arrive as FLOAT64.

SELECT
    event_id,
    event_type,
    TIMESTAMP(event_time) AS event_time,
    TIMESTAMP(emitted_at) AS emitted_at,
    session_id,
    buyer_id,
    p_id,
    price,
    CAST(qty AS INT64) AS qty,
    CAST(order_id AS INT64) AS order_id,
    payment_method,
    amount,
    currency,
    items
FROM {{ source('marketplace', 'clickstream') }}
QUALIFY ROW_NUMBER() OVER (PARTITION BY event_id, emitted_at ORDER BY event_time) = 1
