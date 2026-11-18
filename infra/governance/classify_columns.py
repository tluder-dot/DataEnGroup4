#!/usr/bin/env python3
"""Classify every column of the platform and write it into docs/governance.md.

What it reads: only BigQuery metadata, `INFORMATION_SCHEMA.COLUMNS` of the four
datasets (names and types). It never reads a row of data, so it processes no
table bytes. The queries are the constant strings in COLUMNS_SQL below, and the
script refuses to run any other SQL.

What it writes: the part of docs/governance.md between the two GENERATED
markers. Everything outside the markers is written by hand and left alone.

Rerun it (needs `gcloud auth login` and the `bq` command):

    python infra/governance/classify_columns.py

Metadata last read: 2026-11-19
Rules: the CLASS and REASON tables below. A column whose name matches no rule is
`internal`; the script lists those columns when it runs, so that a new column
never becomes `internal` without somebody looking at it.
"""
import argparse
import collections
import csv
import datetime
import io
import re
import shutil
import subprocess
import sys

PROJECT = "data-engineering-i1"
LOCATION = "europe-west1"
DATASETS = [
    ("g04_bronze_1", "Bronze"),
    ("g04_silver", "Silver"),
    ("g04_gold", "Gold"),
    ("g04_warehouse", "Warehouse"),
]
BEGIN = "<!-- BEGIN GENERATED: infra/governance/classify_columns.py -->"
END = "<!-- END GENERATED -->"

# The only SQL this script runs: names and types from the metadata views.
COLUMNS_SQL = (
    "SELECT table_name, column_name, data_type "
    "FROM `{project}.{dataset}`.INFORMATION_SCHEMA.COLUMNS "
    "ORDER BY table_name, ordinal_position"
)

ID, CON, LOC = "pii.identifier", "pii.contact", "pii.location"
UNC, INT = "unclassified", "internal"
CLASSES = ["public", "internal", "pii.location", "pii.identifier",
           "pii.contact", "unclassified", "secret"]

# Class by column name. Anything not listed is `internal`.
CLASS = {
    "buyer_id": ID, "c_id": ID, "seller_id": ID, "address_id": ID,
    "fname": CON, "lname": CON, "phone": CON, "email": CON,
    "street_address": CON, "billing_address": CON, "seller_name": CON,
    "expiry_date": CON,
    "city": LOC, "state": LOC, "zip": LOC,
    "r_desc": UNC, "title": UNC, "review_text": UNC, "review_title": UNC,
    "review_img": UNC, "extra_fields": UNC, "raw": UNC, "p_desc": UNC,
}
# Identifiers: a row that carries one makes `country` a location.
ROW_IDENTIFIERS = {"buyer_id", "c_id", "seller_id", "address_id"}

REASON = {
    "csv_index": "Row number the export added; no meaning",
    "buyer_id": "Pseudonymous ID of a person; still personal data because it joins to orders, addresses and reviews",
    "c_id": "Pseudonymous ID of a customer; joins to the buyer or seller it equals",
    "seller_id": "Pseudonymous ID of a seller, who may be a person",
    "address_id": "Key of one customer's address; joins to the customer, so it points to one person",
    "fname": "First name; directly identifies a person",
    "lname": "Last name; directly identifies a person",
    "phone": "Phone number; reaches a person directly",
    "email": "Email address; reaches a person directly",
    "street_address": "Street address; reaches a person directly",
    "billing_address": "Billing address; reaches a person directly",
    "seller_name": "Name of a seller, who may be a person",
    "expiry_date": "No card class in the scale; card data linked to a customer, so it takes the strictest personal-data class",
    "city": "Town where a person lives",
    "state": "Region where a person lives",
    "zip": "Postcode where a person lives",
    "r_desc": "Free text typed by a reviewer; may contain anything",
    "title": "Free text typed by a reviewer; may contain anything",
    "review_text": "Free text typed by a reviewer; may contain anything",
    "review_title": "Free text typed by a reviewer; may contain anything",
    "review_img": "Link to an image a reviewer uploaded; a photo can show anything",
    "extra_fields": "Fields the schema does not know, as JSON text; can hold anything",
    "raw": "The rejected message exactly as it arrived; can hold anything, including a buyer_id",
    "p_desc": "Free text written by sellers; may contain anything",
    "p_name": "Short product title; no personal content expected",
    "product_name": "Short product title; no personal content expected",
    "session_id": "Random UUID per visit; follows no one from one visit to the next",
    "order_id": "Order key; no personal content on its own",
}
# Columns read one by one and judged `internal`: quantities, statuses, types and
# labels the company defines. A column in neither this set nor a rule above is
# new, and the script lists it for review.
REVIEWED_INTERNAL = {
    "c_desc", "carrier_name", "category_name", "country_code", "currency",
    "d_desc", "discount_name", "event_type", "has_rating_above_four",
    "is_default", "items", "method", "n_buyers", "n_reviews", "name",
    "order_count", "p_image", "payment_method", "qty", "rating",
    "seller_product_flag", "seller_type", "shipment_type", "status",
    "stock_qty", "total_qty", "units", "units_sold",
}
TIME_COLUMNS = {"order_year", "dt", "month", "year", "quarter", "iso_week",
                "day_of_week", "is_weekend", "event_time", "emitted_at", "created_at"}
AMOUNT_COLUMNS = {"price", "amount", "price_at_purchase", "line_revenue",
                  "gross_revenue", "revenue", "total_price", "discount",
                  "discount_amt", "avg_rating"}
KEY_COLUMNS = {"demand_key", "schema_version", "event_id", "transaction_id",
               "shipping_id", "return_id", "cart_id"}


def default_reason(column):
    if column.endswith("_date") or column in TIME_COLUMNS:
        return "Date or time; no personal content"
    if column in AMOUNT_COLUMNS:
        return "Amount or rating; no personal content"
    if column.endswith("_id") or column in KEY_COLUMNS:
        return "Key; no personal content on its own"
    return None


def classify(column, columns_of_table):
    """Return (class, reason, matched_a_rule)."""
    if column == "country":
        if ROW_IDENTIFIERS & set(columns_of_table):
            return (LOC, "Country on a row that carries an identifier: where one person "
                    "lives (rule: the class depends on the identifier on the row)", True)
        return (INT, "Country with no identifier on the row (aggregated or lookup); "
                "no personal content", True)
    if column in CLASS:
        return CLASS[column], REASON[column], True
    if column in REASON:
        return INT, REASON[column], True
    pattern = default_reason(column)
    reviewed = column in REVIEWED_INTERNAL
    return INT, pattern or "No personal content", pattern is not None or reviewed


def owner(dataset, table):
    if dataset == "g04_bronze_1":
        return "Jane" if table.startswith("clickstream") else "Till"
    if dataset in ("g04_silver", "g04_gold"):
        return "Till"
    return "Enzo"


def kind(dataset, table):
    if dataset == "g04_bronze_1":
        return "external table"
    if dataset == "g04_silver":
        return "table" if table == "country_codes" else "view"
    if dataset == "g04_gold":
        return "table"
    return "materialised view" if table.endswith("_mv") else "table"


def read_columns(dataset):
    """Names and types of one dataset's columns, from its metadata view."""
    sql = COLUMNS_SQL.format(project=PROJECT, dataset=dataset)
    if not re.fullmatch(r"SELECT table_name, column_name, data_type FROM "
                        r"`[\w.-]+`\.INFORMATION_SCHEMA\.COLUMNS ORDER BY table_name, ordinal_position", sql):
        sys.exit("refusing to run SQL that is not a metadata read")
    bq = shutil.which("bq")
    if bq is None:
        sys.exit("the bq command was not found; install the Google Cloud SDK")
    out = subprocess.run(
        [bq, f"--project_id={PROJECT}", f"--location={LOCATION}", "query",
         "--nouse_legacy_sql", "--use_cache=false", "--format=csv",
         "--max_rows=5000", sql],
        capture_output=True, text=True, check=True).stdout
    tables = collections.OrderedDict()
    for row in csv.DictReader(io.StringIO(out)):
        tables.setdefault(row["table_name"], []).append((row["column_name"], row["data_type"]))
    if not tables:
        sys.exit(f"no columns read for {dataset}: check gcloud auth login")
    return tables


def render(read_on):
    sections, totals, defaulted = [], collections.OrderedDict(), []
    for dataset, label in DATASETS:
        tables = read_columns(dataset)
        counts = collections.Counter()
        part = [f"### {label}: `{dataset}`\n"]
        for table, columns in tables.items():
            names = [c for c, _ in columns]
            part.append(f"#### `{dataset}.{table}` ({kind(dataset, table)}, "
                        f"owner: {owner(dataset, table)})\n")
            part += ["| Column | Type | Class | Why |", "|---|---|---|---|"]
            for column, data_type in columns:
                cls, why, matched = classify(column, names)
                if not matched and column != "country":
                    defaulted.append(f"{dataset}.{table}.{column}")
                counts[cls] += 1
                part.append(f"| `{column}` | {data_type.replace('|', '/')} | `{cls}` | {why} |")
            part.append("")
        totals[label] = (len(tables), sum(counts.values()), counts)
        sections.append("\n".join(part))

    summary = ["| Layer | Tables and views | Columns | "
               + " | ".join(f"`{c}`" for c in CLASSES) + " |",
               "|---|---|---|" + "---|" * len(CLASSES)]
    for label, (n_tables, n_columns, counts) in totals.items():
        summary.append(f"| {label} | {n_tables} | {n_columns} | "
                       + " | ".join(str(counts.get(c, 0)) for c in CLASSES) + " |")

    block = "\n".join([
        BEGIN, "",
        "## Summary", "",
        f"Columns per class, read from the metadata of the four datasets on {read_on}, "
        "no row read.", "",
        *summary, "",
        "Not in this count: the dead letter queue files `bronze/_dlq/clickstream/`, "
        "which are in the bucket and not in BigQuery. Their `raw` column is "
        "`unclassified`, owner Jane.", "",
        "## The classification, column by column", "",
        "`csv_index` is the export's row number: it is on every table read from the "
        "export, and is `internal` each time.", "",
        "\n".join(sections), END])
    return block, defaulted


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--doc", default="docs/governance.md")
    parser.add_argument("--date", default=datetime.date.today().isoformat(),
                        help="the date the metadata is read, default today")
    args = parser.parse_args()

    text = open(args.doc, encoding="utf-8").read()
    if BEGIN not in text or END not in text:
        sys.exit(f"{args.doc} has no GENERATED markers")
    block, defaulted = render(args.date)
    head, rest = text.split(BEGIN, 1)
    tail = rest.split(END, 1)[1]
    with open(args.doc, "w", encoding="utf-8", newline="\n") as f:
        f.write(head + block + tail)
    print(f"wrote {args.doc}")
    if defaulted:
        print(f"{len(defaulted)} columns matched no rule and defaulted to internal; "
              "review them:", file=sys.stderr)
        for name in defaulted:
            print("  " + name, file=sys.stderr)


if __name__ == "__main__":
    main()
