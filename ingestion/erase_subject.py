#!/usr/bin/env python3
"""Find, count and remove one person's rows in the bronze Parquet files.

Used by the erasure runbook (docs/runbooks/erasure.md). It looks in both bronze
paths (the export, bronze/<table>/, and the extractor, bronze/postgres/<table>/),
in the clickstream and in its dead letter queue.

The person's identifier is read from the environment, never from the command
line, and is never printed, logged or put in a query:

    SUBJECT_ID=<the identifier> python ingestion/erase_subject.py

Without --apply nothing is written: it counts, per table, the files read, the
rows read and the rows that belong to the person. With --apply it rewrites each
file that holds such rows, without them, and reads the file back to check that
none is left and that no other row was lost. A rewritten object becomes a new
version of the object: the old one stays recoverable for the bucket's soft
delete period (7 days).

Only the rows of the person are removed from a file, so the other people's rows
and the file's schema are kept. A file whose rows all belong to the person is
rewritten as an empty file, so that the external tables still read it.

--apply on the production prefix needs --production. The runbook says who may
use it.
"""
import argparse
import json
import os
import sys
import time

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.fs as pafs
import pyarrow.parquet as pq

BUCKET = "data-engineering-i1-g04"
PRODUCTION_PREFIX = f"gs://{BUCKET}/bronze"

# How each table holds the person. ("subject", column): the column holds the
# identifier itself (a buyer_id, a c_id or a seller_id, the same value for one
# person). ("key", name, column): the column holds a key that the person's other
# rows lead to.
SPEC = {
    "buyer": [("subject", "buyer_id")],
    "orders": [("subject", "buyer_id")],
    "cart": [("subject", "buyer_id")],
    "returns": [("subject", "buyer_id")],
    "review": [("subject", "buyer_id")],
    "wishlist_item": [("subject", "buyer_id")],
    "clickstream": [("subject", "buyer_id")],
    "customer": [("subject", "c_id")],
    "customer_shipping": [("subject", "c_id")],
    "customer_payment": [("subject", "c_id")],
    "subscription": [("subject", "c_id")],
    "seller": [("subject", "seller_id")],
    "seller_products": [("subject", "seller_id")],
    "seller_reviews": [("subject", "seller_id"), ("key", "review_id", "review_id")],
    "order_items": [("key", "order_id", "order_id")],
    "shipment": [("key", "order_id", "order_id")],
    "payment": [("key", "order_id", "order_id")],
    "shipping_details": [("key", "address_id", "address_id")],
    "payment_details": [("key", "payment_id", "payment_id")],
    "review_images": [("key", "review_id", "review_id")],
    "product_reviews": [("key", "review_id", "review_id")],
}
# The keys, read from the person's own rows before anything is changed.
KEYS = {
    "order_id": ("orders", "order_id"),
    "address_id": ("customer_shipping", "address_id"),
    "payment_id": ("customer_payment", "payment_id"),
    "review_id": ("review", "review_id"),
}
# Folders that hold the files of one table, under the prefix.
ROOTS = ("{t}", "postgres/{t}", "postgres/_incremental/{t}")
DLQ = "_dlq/clickstream"  # rejected events: the whole message is in one column


def open_fs(prefix):
    """The file system and the path of a prefix, on the bucket or on a folder."""
    if prefix.startswith("gs://"):
        return pafs.GcsFileSystem(), prefix[len("gs://"):].rstrip("/")
    return pafs.LocalFileSystem(), prefix.replace("\\", "/").rstrip("/")


def parquet_files(fs, root):
    infos = fs.get_file_info(pafs.FileSelector(root, allow_not_found=True, recursive=True))
    return sorted(i.path for i in infos if i.type == pafs.FileType.File and i.path.endswith(".parquet"))


def read(fs, path):
    with fs.open_input_file(path) as f:
        return pq.read_table(f)


def match_mask(table, criteria, subject, keys):
    """True for each row that belongs to the person, or None if no column is there."""
    mask = None
    for criterion in criteria:
        column = criterion[-1]
        if column not in table.column_names:
            continue
        if criterion[0] == "subject":
            this = pc.equal(pc.cast(table[column], pa.string()), pa.scalar(subject))
        else:
            values = keys.get(criterion[1], [])
            this = pc.is_in(table[column], value_set=pa.array(values, type=table[column].type))
        this = pc.fill_null(this, False)
        mask = this if mask is None else pc.or_(mask, this)
    return mask


def dlq_mask(table, subject):
    if "raw" not in table.column_names:
        return None
    return pc.fill_null(pc.match_substring(pc.cast(table["raw"], pa.string()), subject), False)


def scan(fs, base, make_mask, apply):
    """Read every file under base. Return rows read, rows matched, files matched, keys."""
    rows = matched = 0
    files = []
    for path in parquet_files(fs, base):
        table = read(fs, path)
        rows += table.num_rows
        mask = make_mask(table)
        if mask is None:
            continue
        n = pc.sum(pc.cast(mask, pa.int64())).as_py() or 0
        if not n:
            continue
        matched += n
        files.append((path, n, table.num_rows))
        if apply:
            rewrite(fs, path, table, mask, make_mask)
    return rows, matched, files


def rewrite(fs, path, table, mask, make_mask):
    kept = table.filter(pc.invert(mask))
    with fs.open_output_stream(path) as out:
        pq.write_table(kept, out, compression="snappy")
    back = read(fs, path)
    left = make_mask(back)
    left_n = pc.sum(pc.cast(left, pa.int64())).as_py() or 0
    if back.num_rows != kept.num_rows or left_n:
        raise RuntimeError(f"check failed after rewriting {path}: {back.num_rows} rows, {left_n} left")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--prefix", default=PRODUCTION_PREFIX,
                        help="gs://... or a local folder that holds the bronze layout")
    parser.add_argument("--apply", action="store_true", help="rewrite the files (default: count only)")
    parser.add_argument("--production", action="store_true",
                        help="allow --apply on the production bronze prefix")
    parser.add_argument("--label", default="subject A", help="how the report names the person")
    parser.add_argument("--report", help="write the counts, without any identifier, to this JSON file")
    args = parser.parse_args()

    subject = os.environ.get("SUBJECT_ID", "")
    if len(subject) < 8:
        sys.exit("SUBJECT_ID is missing or too short")
    if args.apply and args.prefix.rstrip("/") == PRODUCTION_PREFIX and not args.production:
        sys.exit("refusing --apply on the production prefix without --production")

    fs, base = open_fs(args.prefix)
    mode = "APPLY" if args.apply else "DRY RUN (nothing is written)"
    print(f"{mode}: {args.label}, prefix {args.prefix}")
    started = time.perf_counter()
    report = {"label": args.label, "prefix": args.prefix, "applied": args.apply, "tables": {}}

    def run(name, root_templates, make_mask, apply):
        total = [0, 0, []]
        for template in root_templates:
            rows, matched, files = scan(fs, f"{base}/{template.format(t=name)}", make_mask, apply)
            total[0] += rows
            total[1] += matched
            total[2] += files
        status = "0 rows of the person" if not total[1] else f"{total[1]} rows of the person"
        print(f"  {name:18s} {total[0]:9d} rows read, {status}")
        for path, n, size in total[2]:
            print(f"      {path[len(base) + 1:]}: {n} of {size}")
        report["tables"][name] = {"rows_read": total[0], "rows_matched": total[1],
                                  "files_matched": [p[len(base) + 1:] for p, _, _ in total[2]]}
        return total

    # 1. The keys, read from the person's own rows before anything is changed: a
    # rewrite removes those rows, and the keys would be lost with them.
    print("1. Keys that lead from the person to the other tables")
    keys = {}
    for key, (table_name, column) in KEYS.items():
        values = set()
        for template in ROOTS:
            for path in parquet_files(fs, f"{base}/{template.format(t=table_name)}"):
                table = read(fs, path)
                mask = match_mask(table, SPEC[table_name], subject, keys)
                if mask is not None and column in table.column_names:
                    values.update(table.filter(mask)[column].to_pylist())
        keys[key] = sorted(values)
    print("   found: " + ", ".join(f"{k} {len(v)}" for k, v in keys.items()))

    def every_table(apply):
        found = 0
        for name, criteria in SPEC.items():
            roots = ("clickstream",) if name == "clickstream" else ROOTS
            found += run(name, roots, lambda t, c=criteria: match_mask(t, c, subject, keys), apply)[1]
        found += run("_dlq/clickstream", (DLQ,), lambda t: dlq_mask(t, subject), apply)[1]
        return found

    # 2. Count, or rewrite.
    print("2. " + ("Rewriting the files without the person's rows" if args.apply
                   else "Rows of the person, table by table"))
    every_table(args.apply)

    # 3. After a rewrite, count again: every table must say 0.
    if args.apply:
        print("3. Counting again")
        report["tables_before_rewrite"] = report["tables"]
        report["tables"] = {}
        left = every_table(False)
        report["rows_left"] = left
        if left:
            sys.exit(f"{left} rows of the person are still there")

    report["seconds"] = round(time.perf_counter() - started, 1)
    print(f"done in {report['seconds']} s")
    if args.report:
        with open(args.report, "w", encoding="ascii") as f:
            json.dump(report, f, indent=2)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # the identifier must not leak through an error message
        message = str(exc).replace(os.environ.get("SUBJECT_ID", "\0"), "<subject>")
        sys.exit(f"error: {type(exc).__name__}: {message}")
