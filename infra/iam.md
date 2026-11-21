# Access

Every binding on the group's bucket and bronze dataset, copied from
`gcloud storage buckets get-iam-policy gs://data-engineering-i1-g04` and
`bq show --format=prettyjson data-engineering-i1:g04_bronze_1` on
6 November 2026.

**There is no service account.** Groups get none in this project (Charles), so
every job runs as one of our personal Google logins.

## Bucket `gs://data-engineering-i1-g04`

Uniform bucket-level access, so there are no per-object permissions. The
bucket has only the bindings Cloud Storage gives every new bucket. We added
none.

| Principal | Role | Scope | Why |
|---|---|---|---|
| `projectOwner:data-engineering-i1` | `roles/storage.legacyBucketOwner`, `roles/storage.legacyObjectOwner` | Bucket | Default: the project's owners manage every bucket |
| `projectEditor:data-engineering-i1` | `roles/storage.legacyBucketOwner`, `roles/storage.legacyObjectOwner` | Bucket | Default: the project's editors can write and delete |
| `projectViewer:data-engineering-i1` | `roles/storage.legacyBucketReader`, `roles/storage.legacyObjectReader` | Bucket | Default: the project's viewers can list and read the files |

Our own logins get their rights from roles the course set on the project. We
cannot list them: `gcloud projects get-iam-policy` is refused. What Till's
login could do: create a bucket (L02 Exercise 1) and this dataset, write
objects, apply the lifecycle rule. What it could not: create a service
account.

## Dataset `g04_bronze_1`

| Principal | Role | Scope | Why |
|---|---|---|---|
| `projectOwners` | Owner | Dataset | Default, kept: the project's owners |
| Till | Owner | Dataset | Created the dataset and runs the landing script |
| Enzo | Owner | Dataset | Manages the dataset with Terraform (L08) |
| Evaluna, Jane | `roles/bigquery.dataViewer` | Dataset | Read bronze for the dbt models (L05) and the governance work (L10) |

`projectReaders` and `projectWriters`, which BigQuery adds to every new
dataset, were removed on 3 November. Bronze holds names, addresses and phone
numbers ([data dictionary](../docs/data-dictionary.md)), so only named people
read it.

How it was set:

```
bq --location=europe-west1 query --nouse_legacy_sql \
  'GRANT `roles/bigquery.dataViewer` ON SCHEMA `data-engineering-i1`.g04_bronze_1
   TO "user:<member>@albertschool.com", ...'
bq show --format=prettyjson data-engineering-i1:g04_bronze_1 > access.json
# delete the projectReaders and projectWriters entries from "access", then:
bq update --source access.json data-engineering-i1:g04_bronze_1
```

## Datasets `g04_silver` and `g04_gold`

Created on 6 November 2026, with the same default groups removed. Silver holds
buyer IDs and review text.

| Principal | Role | Scope | Why |
|---|---|---|---|
| `projectOwners` | Owner | Dataset | Default, kept: the project's owners |
| Till | Owner | Dataset | Created the datasets and runs dbt |
| Enzo | Owner | Dataset | Manages the datasets with Terraform (L08) |
| Jane | `roles/bigquery.dataEditor` | Dataset | Airflow rebuilds silver and gold (L07) |
| Evaluna | `roles/bigquery.dataViewer` | Dataset | Reads silver and gold to count and check (L10). Narrowed from Writer on 20 Nov 2026, see below |

**Evaluna's Writer became Reader on silver and gold** (`roles/bigquery.dataEditor`
to `roles/bigquery.dataViewer`). `lastModifiedTime` of the datasets: `g04_silver`
20 November 2026 at 11:49:48 UTC, `g04_gold` at 11:50:05 UTC. Applied by Evaluna
herself, with the agreement asked of Till, who owns both datasets and had not yet
answered. She writes nothing there: dbt builds silver and gold, run by Till and by
Jane's DAG. The Writer role was given for L10 to classify and protect the columns,
but classifying is a document ([governance](../docs/governance.md)), and a policy
tag can only go on a native table, which silver (views) is not. A Writer can also
read `buyer_id` and delete tables; a Reader has what counting and checking need.

**What this did not change, and what it showed.** `testIamPermissions`, read-only:

| When (UTC, 20 Nov 2026) | What the login could do |
|---|---|
| 11:00:00, before | `update`, `updateData` and `delete` on tables of `g04_silver`, `g04_gold` and on `g04_warehouse.orders_month`, where the dataset lists no entry for her |
| 11:44:59, before, with only Writer at dataset level | `datasets.update`, `datasets.setIamPolicy` and `datasets.delete` on `g04_silver` and `g04_gold`. The Writer role does not include them |
| 11:50:22, after | The same, on the same tables and datasets |

So a project-level role that we cannot list gives more than the dataset says, and
the narrowing changed the dataset's list, not what the login can do. It also means
that **any member with that project-level role can change the access of these
datasets, or delete them, without being their Owner**: Evaluna changed her own
entry that way. See gap 10 in [governance](../docs/governance.md).

How it was changed, for each of the two datasets:

```
bq show --format=prettyjson data-engineering-i1:g04_silver > before.json
python swap_own_grant.py before.json after.json <evaluna>@albertschool.com
bq update --source after.json data-engineering-i1:g04_silver
bq show --format=prettyjson data-engineering-i1:g04_silver     # READER for her, no WRITER
```

`swap_own_grant.py` replaces that login's WRITER entry by a READER entry, and
refuses to write if it does not find exactly one such entry or if anything else
would change:

```python
import json, sys
src, dst, who = sys.argv[1:4]
j = json.load(open(src, encoding="utf-8-sig"))
before = j["access"]
old = {"role": "WRITER", "userByEmail": who}
new = {"role": "READER", "userByEmail": who}
if before.count(old) != 1 or new in before:
    sys.exit("REFUSED: not exactly one WRITER entry for that login, or a READER entry already exists")
others = [a for a in before if a != old]
after = others + [new]
key = lambda a: json.dumps(a, sort_keys=True)
if len(after) != len(before) or sorted(map(key, others)) != sorted(map(key, [a for a in after if a != new])):
    sys.exit("REFUSED: something else would change")
j["access"] = after
json.dump(j, open(dst, "w", encoding="ascii"), indent=2)
```

## Dataset `g04_warehouse`

Native tables and materialised views of step 4. Read back with the BigQuery API
(`get_dataset`, access entries) on 6 November 2026.

| Principal | Role | Scope | Why |
|---|---|---|---|
| `projectOwners` | Owner | Dataset | Default, kept: the project's owners |
| Enzo | Owner | Dataset | Created the dataset and manages it with Terraform (L08) |
| Jane | `roles/bigquery.dataViewer` | Dataset | Reads the warehouse for the pipeline (L07) |

`projectReaders` and `projectWriters` were removed on 6 November: until then
any Viewer or Editor of the project could read the warehouse. It holds the
orders, order lines, reviews and the customer-to-address link;
`shipping_details` keeps only `address_id` and `country`, so it has no street or
phone ([tuning](../docs/warehouse-tuning.md)). Evaluna and Till have no grant
here. No file under `transform/` reads `g04_warehouse` (searched on
6 November), so dbt does not need one.

## Not handled

- **Anyone with Viewer on the project can read the bronze files** through the
  bucket's `projectViewer` binding, without access to the dataset. We cannot
  see who holds Viewer, so we do not know whether removing it would also cut
  off our own reads. It stays until L10 tightens access.
