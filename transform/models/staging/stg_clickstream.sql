-- One row per event. The consumer delivers at least once, so a crash writes a
-- batch twice: keeps the first copy of each event_id (ADR 0003).
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
QUALIFY ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY emitted_at) = 1
