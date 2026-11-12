"""Read clickstream events from Kafka and land them in bronze as partitioned Parquet.

Delivery guarantee: at least once, because flush() writes each file to the
bucket before it commits the Kafka offset, so a crash between the two re-reads
the batch and writes some events twice, but never loses one.

Files are partitioned by event_time (dt=YYYY-MM-DD), the same simulated clock
as order_date, so a day of clicks lines up with the same day of orders.
emitted_at stays a column, so a later layer can partition by arrival instead.
Rejected events go to the DLQ, partitioned by the time they were rejected.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import fsspec
import pyarrow as pa
import pyarrow.parquet as pq
from confluent_kafka import Consumer
from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match

# Everything that changes between runs arrives in the environment, which is
# what lets the same file serve the demo, the exercise and your project.
BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP", "localhost:9092")
TOPIC = os.environ.get("KAFKA_TOPIC", "clickstream")
# Square brackets, so a missing group fails immediately and loudly. It has no
# sensible default: the group IS where Kafka stores how far you have read, so
# picking one for you would silently resume somebody else's progress.
GROUP = os.environ["CONSUMER_GROUP"]           # your own: clickstream-<initials>
# Group 4's bronze layer by default. For a local test, set OUT and DLQ to a
# folder such as out/bronze/clickstream, so test rows never reach bronze.
OUT = os.environ.get("OUT", "gs://data-engineering-i1-g04/bronze/clickstream")
DLQ = os.environ.get("DLQ", "gs://data-engineering-i1-g04/bronze/_dlq/clickstream")
BATCH = int(os.environ.get("BATCH", "200"))    # most rows per file
# Write at the latest this many seconds after the first buffered message, even
# if the batch is not full. Files of 1 to 11 rows were written on 5 November,
# one per quiet second; 15 minutes gives far bigger files, and a crash never
# replays more than 15 minutes of events.
FLUSH_EVERY = float(os.environ.get("FLUSH_EVERY_S", "900"))
# Seconds between writing and committing. 0 in normal use; the demo sets it to
# 20 so the window is wide enough to kill the process inside.
PAUSE = float(os.environ.get("PAUSE_BEFORE_COMMIT", "0"))

# One validator per schema_version: each event is checked against the schema
# of the version it says it is. A new version adds a file and a line here.
SCHEMAS = {
    1: Draft202012Validator(json.loads(
        Path(__file__).with_name("clickstream.schema.json").read_text())),
}

# The same columns and types in every file, as declared in
# ingestion/clickstream_external.sql: a batch without an order still has
# order_id (empty), and qty is always a double. Fields the schema does not
# know are kept, as JSON text, in extra_fields, so no file grows a column of
# its own.
EVENT_SCHEMA = pa.schema([
    ("schema_version", pa.int64()),
    ("event_id", pa.string()),
    ("event_type", pa.string()),
    ("event_time", pa.string()),
    ("emitted_at", pa.string()),
    ("session_id", pa.string()),
    ("buyer_id", pa.string()),
    ("p_id", pa.string()),
    ("price", pa.float64()),
    ("qty", pa.float64()),
    ("order_id", pa.float64()),
    ("payment_method", pa.string()),
    ("amount", pa.float64()),
    ("currency", pa.string()),
    ("items", pa.list_(pa.struct([("p_id", pa.string()),
                                  ("qty", pa.int64()),
                                  ("price", pa.float64())]))),
    ("extra_fields", pa.string()),
])
DLQ_SCHEMA = pa.schema([
    ("raw", pa.string()),
    ("reason", pa.string()),
    ("rejected_at", pa.string()),
    ("topic", pa.string()),
    ("partition", pa.int64()),
    ("offset", pa.int64()),
])
KNOWN = set(EVENT_SCHEMA.names) - {"extra_fields"}

consumer = Consumer({
    "bootstrap.servers": BOOTSTRAP,
    "group.id": GROUP,
    # Start from the beginning when this group has never read before. A new
    # group name therefore replays the whole topic, which is how you re-run the
    # exercise from scratch.
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False,               # committed by hand. That is the lesson.
})
consumer.subscribe([TOPIC])

# Accumulated between flushes: good rows, quarantined rows, and a running total
# for the output.
good, bad = [], []
written = 0
first_at = None                                # when the buffer got its first row


def write(rows, root, schema, time_field):
    """One Parquet file per date of time_field, under dt=YYYY-MM-DD/.

    Events are filed by event_time: the day it happened, not the day it reached
    us, so late events land in the day they belong to. Rejected events are
    filed by rejected_at. Every file has exactly the columns of schema.
    """
    by_day = {}
    for row in rows:
        # The schema and the date check guarantee YYYY-MM-DD at the start.
        by_day.setdefault(row[time_field][:10], []).append(row)
    # A timestamp in the filename, so two runs never overwrite each other.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    for dt, part in sorted(by_day.items()):
        folder = f"{root}/dt={dt}"
        # A gs:// path is an object prefix, not a folder: there is nothing to
        # create, and os.makedirs would make a local folder named "gs:".
        if not root.startswith("gs://"):
            os.makedirs(folder, exist_ok=True)
        path = f"{folder}/part-{stamp}.parquet"
        # from_pylist fills a missing field with null and casts to the schema's
        # type. dt is not stored: it is in the path.
        table = pa.Table.from_pylist(part, schema=schema)
        with fsspec.open(path, "wb") as f:     # local folder or gs://
            pq.write_table(table, f)
        print(f"  wrote {len(part):4d} rows  {path}")


def flush():
    """Write everything buffered, then commit. In that order, on purpose."""
    global good, bad, written, first_at
    if not good and not bad:
        return
    if good:
        write(good, OUT, EVENT_SCHEMA, "event_time")
        written += len(good)
    if bad:
        write(bad, DLQ, DLQ_SCHEMA, "rejected_at")  # the reason travels with the row
        print(f"  {len(bad)} row(s) quarantined")
    # The window. Everything above has happened; nothing below has.
    #
    # Crash here and the offset is NOT committed, so the next run reads this
    # batch again and writes some rows twice - at-least-once. Swap these two
    # steps and a crash here loses the batch instead, permanently and without
    # a word: at-most-once. Duplicates you can find and remove. Silence you
    # cannot.
    if PAUSE:
        print(f"  ... {PAUSE}s before committing the offset. Kill me now.")
        time.sleep(PAUSE)
    # asynchronous=False: do not return until Kafka has stored the offset, so
    # "committed" in the log means committed.
    consumer.commit(asynchronous=False)
    print(f"  offset committed   (rows written so far: {written})")
    good, bad = [], []
    first_at = None


def due():
    """The buffer is full, or its first row has waited FLUSH_EVERY seconds."""
    if not good and not bad:
        return False
    return (len(good) + len(bad) >= BATCH
            or time.monotonic() - first_at >= FLUSH_EVERY)


print(f"reading {TOPIC} from {BOOTSTRAP} as group {GROUP}")
print(f"writing to {OUT}, at most {BATCH} rows or every {FLUSH_EVERY:.0f} s\n")
try:
    while True:
        # Wait up to a second for a message. None means the topic is quiet.
        msg = consumer.poll(1.0)
        if msg is None:
            if due():                          # quiet, but the wait is over
                flush()
            continue
        if msg.error():
            print(f"  kafka error: {msg.error()}")
            continue
        if first_at is None:
            first_at = time.monotonic()
        raw = msg.value().decode("utf-8")
        try:
            event = json.loads(raw)
            if not isinstance(event, dict):
                raise ValueError("not a JSON object")
            version = event.get("schema_version")
            if version not in SCHEMAS:
                raise ValueError(f"unknown schema_version: {version!r}")
            error = best_match(SCHEMAS[version].iter_errors(event))
            if error is not None:
                raise ValueError(f"schema v{version}: {error.message}")
            # The schema checks the shape of event_time; this checks it is a
            # real date, so one impossible date cannot crash write() for the
            # whole batch.
            datetime.fromisoformat(event["event_time"].replace("Z", "+00:00"))
            extra = {k: v for k, v in event.items() if k not in KNOWN}
            if extra:
                event = {k: v for k, v in event.items() if k in KNOWN}
                event["extra_fields"] = json.dumps(extra)
            good.append(event)
        except Exception as exc:               # malformed: quarantine, never drop
            # Everything needed to find the message again goes with it: one bad
            # row must never stop the stream, and must never vanish either.
            bad.append({"raw": raw, "reason": str(exc),
                        "rejected_at": datetime.now(timezone.utc).isoformat(),
                        "topic": msg.topic(), "partition": msg.partition(),
                        "offset": msg.offset()})
        if due():
            flush()
except KeyboardInterrupt:
    # Not a tidy shutdown. os._exit skips every cleanup handler, so nothing is
    # flushed and nothing is committed - which is what a crash looks like, and
    # what section 4 of the demo needs it to look like.
    print("\nkilled")
    os._exit(1)
