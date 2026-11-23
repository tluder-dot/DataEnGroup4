"""Is a read of a tagged column refused? A policy tag test on synthetic data.

It creates a taxonomy with fine-grained access control, one tag nobody is granted,
and a table of 3 synthetic rows with the tag on buyer_id, then reads the tagged
column and the untagged ones with the login that runs it (ADC). Results are in
docs/governance.md, "Enforcement: what was tested".

    python infra/governance/policy_tag_test.py run       # create, tag, read
    python infra/governance/policy_tag_test.py read      # only the two reads again
    python infra/governance/policy_tag_test.py cleanup   # delete what `run` created

Needs google-cloud-bigquery and google-cloud-datacatalog. Everything is named g04;
nothing outside g04 is touched.
"""
import sys

from google.api_core import exceptions as gex
from google.cloud import bigquery, datacatalog_v1

P, LOC = "data-engineering-i1", "europe-west1"
DATASET, TABLE = "g04_test_tags", "orders_sample"
TAXONOMY = "g04-classification"
FQ = f"{P}.{DATASET}.{TABLE}"

bq = bigquery.Client(project=P)
pt = datacatalog_v1.PolicyTagManagerClient()


def clock():
    return list(bq.query("SELECT FORMAT_TIMESTAMP('%H:%M:%S', CURRENT_TIMESTAMP())").result())[0][0]


def our_taxonomies():
    return [t for t in pt.list_taxonomies(parent=f"projects/{P}/locations/{LOC}")
            if t.display_name == TAXONOMY]


def run():
    if our_taxonomies():
        sys.exit(f"{TAXONOMY} already exists: run cleanup first")
    tax = pt.create_taxonomy(parent=f"projects/{P}/locations/{LOC}", taxonomy=datacatalog_v1.Taxonomy(
        display_name=TAXONOMY,
        description="g04 test of column-level access by a second login. Synthetic data only.",
        activated_policy_types=[datacatalog_v1.Taxonomy.PolicyType.FINE_GRAINED_ACCESS_CONTROL]))
    print(clock(), "taxonomy created, fine-grained access control on")
    tag = pt.create_policy_tag(parent=tax.name,
                               policy_tag=datacatalog_v1.PolicyTag(display_name="pii-identifier"))
    print(clock(), "tag pii-identifier created")

    ds = bigquery.Dataset(f"{P}.{DATASET}")
    ds.location = LOC
    ds.labels = {"group": "g04", "environment": "test", "layer": "test", "lesson": "l10"}
    bq.create_dataset(ds)
    rows = [{"order_id": i, "buyer_id": f"TEST-000{i}", "order_date": "2026-11-23"} for i in (1, 2, 3)]
    schema = [bigquery.SchemaField("order_id", "INT64"),
              bigquery.SchemaField("buyer_id", "STRING"),
              bigquery.SchemaField("order_date", "DATE")]
    bq.load_table_from_json(rows, FQ, job_config=bigquery.LoadJobConfig(schema=schema)).result()
    print(clock(), f"dataset {DATASET} and table {TABLE} created, 3 synthetic rows")

    t = bq.get_table(FQ)
    t.schema = [schema[0],
                bigquery.SchemaField("buyer_id", "STRING", policy_tags=bigquery.PolicyTagList([tag.name])),
                schema[2]]
    bq.update_table(t, ["schema"])
    tagged = [f.name for f in bq.get_table(FQ).schema if f.policy_tags and f.policy_tags.names]
    print(clock(), "tag set; tagged columns:", tagged)
    print("tag IAM bindings (empty = nobody is a fine-grained reader):",
          list(pt.get_iam_policy(request={"resource": tag.name}).bindings))
    read()


def read():
    cfg = bigquery.QueryJobConfig(use_query_cache=False, maximum_bytes_billed=100 * 1024**2)
    for cols in ("buyer_id", "order_id, order_date"):
        try:
            n = len(list(bq.query(f"SELECT {cols} FROM `{FQ}`", job_config=cfg).result()))
            print(clock(), f"SELECT {cols}: {n} rows, no error")
        except gex.GoogleAPICallError as e:
            print(clock(), f"SELECT {cols}: REFUSED: {e.message[:300]}")


def cleanup():
    bq.delete_dataset(f"{P}.{DATASET}", delete_contents=True, not_found_ok=True)
    print(clock(), f"dataset {DATASET} deleted")
    for t in our_taxonomies():
        pt.delete_taxonomy(name=t.name)
        print(clock(), f"taxonomy {t.display_name} deleted, with its tag")
    left = [d.dataset_id for d in bq.list_datasets() if d.dataset_id.startswith("g04")]
    print("g04 datasets now:", left, "| g04 taxonomies now:", len(our_taxonomies()))


{"run": run, "read": read, "cleanup": cleanup}[sys.argv[1]]()
