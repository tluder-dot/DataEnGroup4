"""Read clickstream events from Kafka and write them to partitioned Parquet.

The order of the last two actions in flush() is the entire lesson: write the
file, THEN commit the offset. Read that function before you run anything.
"""

import json
import os
import time
from datetime import datetime, timezone

import pandas as pd
from confluent_kafka import Consumer

# Everything that changes between runs arrives in the environment, which is
# what lets the same file serve the demo, the exercise and your project.
BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP", "localhost:9092")
TOPIC = os.environ.get("KAFKA_TOPIC", "clickstream")
# Square brackets, so a missing group fails immediately and loudly. It has no
# sensible default: the group IS where Kafka stores how far you have read, so
# picking one for you would silently resume somebody else's progress.
GROUP = os.environ["CONSUMER_GROUP"]           # your own: clickstream-<initials>
OUT = os.environ.get("OUT", "out/bronze/clickstream")
DLQ = os.environ.get("DLQ", "out/_dlq/clickstream")
BATCH = int(os.environ.get("BATCH", "200"))    # rows per file
# Seconds between writing and committing. 0 in normal use; the demo sets it to
# 20 so the window is wide enough to kill the process inside.
PAUSE = float(os.environ.get("PAUSE_BEFORE_COMMIT", "0"))

# A row missing any of these cannot be filed by date or joined to anything, so
# it goes to the dead-letter path rather than into bronze.
REQUIRED = ("event_id", "event_type", "event_time", "buyer_id")

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


def write(rows, root):
    """One Parquet file per event date, under dt=YYYY-MM-DD/."""
    df = pd.DataFrame(rows)
    # Filed by event_time: the day it happened, not the day it reached us.
    # Late-arriving events therefore land in the day they belong to, which is
    # the only way a day's partition is ever complete.
    df["dt"] = pd.to_datetime(df["event_time"], format="mixed").dt.strftime("%Y-%m-%d")
    # A timestamp in the filename, so two runs never overwrite each other.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    for dt, part in df.groupby("dt"):
        folder = os.path.join(root, f"dt={dt}")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"part-{stamp}.parquet")
        # drop the dt column: it is in the path, and storing it twice is the
        # small-file tax from lesson 2 paid for nothing.
        part.drop(columns=["dt"]).to_parquet(path, index=False)
        print(f"  wrote {len(part):4d} rows  {path}")


def flush():
    """Write everything buffered, then commit. In that order, on purpose."""
    global good, bad, written
    if not good and not bad:
        return
    if good:
        write(good, OUT)
        written += len(good)
    if bad:
        write(bad, DLQ)                        # the reason travels with the row
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


print(f"reading {TOPIC} from {BOOTSTRAP} as group {GROUP}")
print(f"writing to {OUT}\n")
try:
    while True:
        # Wait up to a second for a message. None means the topic is quiet.
        msg = consumer.poll(1.0)
        if msg is None:
            flush()                            # idle: write what we have
            continue
        if msg.error():
            print(f"  kafka error: {msg.error()}")
            continue
        raw = msg.value().decode("utf-8")
        try:
            event = json.loads(raw)
            missing = [f for f in REQUIRED if f not in event]
            if missing:
                raise ValueError(f"missing field(s): {', '.join(missing)}")
            good.append(event)
        except Exception as exc:               # malformed: quarantine, never drop
            # Everything needed to find the message again goes with it: one bad
            # row must never stop the stream, and must never vanish either.
            bad.append({"raw": raw, "reason": str(exc),
                        "event_time": datetime.now(timezone.utc).isoformat(),
                        "topic": msg.topic(), "partition": msg.partition(),
                        "offset": msg.offset()})
        if len(good) + len(bad) >= BATCH:
            flush()
except KeyboardInterrupt:
    # Not a tidy shutdown. os._exit skips every cleanup handler, so nothing is
    # flushed and nothing is committed - which is what a crash looks like, and
    # what section 4 of the demo needs it to look like.
    print("\nkilled")
    os._exit(1)
