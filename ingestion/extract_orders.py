"""Extract the database tables into bronze as Parquet, with plain SQL.

Delivery guarantee: at least once, because an incremental run writes its file
before it saves the cursor, so a crash between the two reads those rows again.

Two modes (docs/adr/0003-ingestion-modes.md):
- full, the default: rereads the whole table and replaces its files, so after
  each run bronze matches the source, updates and deletes included.
- incremental, orders only: appends the rows from a saved cursor on order_date.
  The cursor sits next to the data, so it survives a restart and works from
  any member's machine.

Choices:
- Columns are selected by name. customer and payment_details are not in
  TABLES, so pwd, card_no and cvv cannot be read.
- Every column has a fixed type, the one it has in the export's bronze tables,
  so no file depends on what one batch happens to contain.
- orders is partitioned by year, as in ADR-0002. The extractor adds no column.
- The export's land_export.py deletes anything else under bronze/<table>/, so
  this path has its own prefix, bronze/postgres/.

Settings come from the environment. DATABASE_URL has no default.

Usage:
    DATABASE_URL=... TABLE=product python ingestion/extract_orders.py
    DATABASE_URL=... MODE=incremental python ingestion/extract_orders.py
"""

import json
import os
import time
from datetime import date, datetime, timezone

import fsspec
import psycopg
import pyarrow as pa
import pyarrow.parquet as pq
from psycopg.rows import dict_row
from psycopg.types.numeric import FloatLoader

DATABASE_URL = os.environ["DATABASE_URL"]
TABLE = os.environ.get("TABLE", "orders")
MODE = os.environ.get("MODE", "full")
OUT = os.environ.get("OUT", "gs://data-engineering-i1-g04/bronze/postgres")
# >= reads the cursor's day again: a row read twice beats a row never read.
CURSOR_OP = os.environ.get("CURSOR_OP", ">=")
RETRIES = int(os.environ.get("RETRIES", "5"))
RETRY_DELAY = float(os.environ.get("RETRY_DELAY", "2"))  # doubles at each try

CURSOR_COLUMN = "order_date"

TEXT, INT, FLOAT, DATE = pa.string(), pa.int64(), pa.float64(), pa.date32()
TABLES = {
    "orders": {
        "order_id": INT, "buyer_id": TEXT, "discount_id": INT,
        "payment_id": INT, "order_date": DATE,
    },
    "order_items": {
        "order_id": INT, "p_id": TEXT, "qty": INT, "price_at_purchase": FLOAT,
    },
    "review": {
        "review_id": INT, "buyer_id": TEXT, "r_desc": TEXT, "title": TEXT,
        "rating": INT, "seller_product_flag": TEXT,
    },
    "product_reviews": {"p_id": TEXT, "review_id": INT},
    "product": {
        "p_id": TEXT, "p_name": TEXT, "p_desc": TEXT, "price": FLOAT,
        "qty": INT, "category_id": INT,
    },
    "customer_shipping": {"address_id": INT, "c_id": TEXT, "is_default": TEXT},
    "shipping_details": {
        "address_id": INT, "street_address": TEXT, "city": TEXT, "state": TEXT,
        "zip": TEXT, "country": TEXT, "phone": TEXT,
    },
}


def read_rows(query: str, params: tuple = ()) -> list[dict]:
    """Run one query. A lost connection is retried, then the run gives up."""
    for attempt in range(1, RETRIES + 1):
        try:
            with psycopg.connect(
                DATABASE_URL, connect_timeout=5, row_factory=dict_row
            ) as conn:
                # numeric as float, the type the export's bronze tables use.
                conn.adapters.register_loader("numeric", FloatLoader)
                return conn.execute(query, params).fetchall()
        except psycopg.OperationalError as exc:
            if attempt == RETRIES:
                raise SystemExit(f"giving up after {RETRIES} attempts: {exc}")
            delay = RETRY_DELAY * 2 ** (attempt - 1)
            print(f"  attempt {attempt} failed, next try in {delay:g} s")
            time.sleep(delay)


def write(rows: list[dict], schema: pa.Schema, path: str) -> None:
    if not path.startswith("gs://"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
    with fsspec.open(path, "wb") as file:
        pq.write_table(
            pa.Table.from_pylist(rows, schema=schema), file, compression="snappy"
        )
    print(f"  wrote {len(rows):7d} rows  {path}")


def extract_full(columns: str, schema: pa.Schema) -> int:
    rows = read_rows(f"SELECT {columns} FROM {TABLE}")
    if TABLE != "orders":
        write(rows, schema, f"{OUT}/{TABLE}/part-0.parquet")
        return len(rows)
    for year in sorted({row[CURSOR_COLUMN].year for row in rows}):
        part = [row for row in rows if row[CURSOR_COLUMN].year == year]
        write(part, schema, f"{OUT}/orders/order_year={year}/part-0.parquet")
    return len(rows)


def load_cursor(path: str) -> date | None:
    try:
        with fsspec.open(path, "r") as file:
            return date.fromisoformat(json.load(file)["cursor"])
    except FileNotFoundError:
        return None


def save_cursor(path: str, cursor: date) -> None:
    if not path.startswith("gs://"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
    with fsspec.open(path, "w") as file:
        json.dump({"cursor": cursor.isoformat()}, file)


def extract_incremental(columns: str, schema: pa.Schema) -> int:
    state = f"{OUT}/_state/{TABLE}.json"
    cursor = load_cursor(state)
    if cursor is None:
        rows = read_rows(f"SELECT {columns} FROM {TABLE}")
    else:
        rows = read_rows(
            f"SELECT {columns} FROM {TABLE} "
            f"WHERE {CURSOR_COLUMN} {CURSOR_OP} %s",
            (cursor,),
        )
    print(f"  cursor {cursor}, {CURSOR_OP}: {len(rows)} rows")
    if rows:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        write(rows, schema, f"{OUT}/_incremental/{TABLE}/part-{stamp}.parquet")
        # After the write, in that order: a crash here reads these rows again.
        save_cursor(state, max(row[CURSOR_COLUMN] for row in rows))
    return len(rows)


def main() -> None:
    if TABLE not in TABLES:
        raise SystemExit(f"{TABLE} is not one of {sorted(TABLES)}")
    if MODE not in ("full", "incremental"):
        raise SystemExit(f"MODE must be full or incremental, not {MODE}")
    if MODE == "incremental" and TABLE != "orders":
        raise SystemExit(f"{TABLE} has no {CURSOR_COLUMN}: use MODE=full")
    if CURSOR_OP not in (">", ">="):
        raise SystemExit(f"CURSOR_OP must be > or >=, not {CURSOR_OP}")

    spec = TABLES[TABLE]
    schema = pa.schema(list(spec.items()))
    columns = ", ".join(spec)
    start = time.perf_counter()
    extract = extract_full if MODE == "full" else extract_incremental
    count = extract(columns, schema)
    print(f"{TABLE}: {count} rows, {MODE}, {time.perf_counter() - start:.1f} s")


if __name__ == "__main__":
    main()
