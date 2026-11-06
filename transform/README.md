# Transform

The dbt project that turns bronze into silver and gold: step 5 of the course.

| Layer | Folder | Becomes | Dataset |
|---|---|---|---|
| Bronze | `models/sources.yml` | Declared, never written | `g04_bronze_1` |
| Silver | `models/staging/`, `models/intermediate/` | Views | `g04_silver` |
| Gold | `models/marts/` | Tables | `g04_gold` |

- **Staging:** one model per source, no joins. Each header names the defect it
  fixes, and the [data dictionary](../docs/data-dictionary.md#traps-in-the-export)
  says where each defect is handled.
- **Intermediate:** the joins, and the rule for twin orders in `int_orders`.
- **Marts:** the star. Each fact states its grain and tests it.

Why views and tables: [ADR 0005](../docs/adr/0005-materialisations.md). What the
tests promise: [acceptance criteria](../docs/acceptance-criteria.md). What feeds
what: [lineage](../docs/lineage.md).

## Run it

It needs Docker and `gcloud auth application-default login`, and nothing else.
From this folder:

```
docker run --rm -e DBT_DATASET=l05_<initials> -e DBT_PROFILES_DIR=/usr/app \
  -v "$PWD:/usr/app" -v "$HOME/.config/gcloud:/root/.config/gcloud:ro" \
  charlestng/dbt-bigquery:1.12.1 deps
```

Then the same command with `build` instead of `deps`, then `source freshness`.
Without `DBT_DATASET` it builds the group's `g04_silver` and `g04_gold`, so keep
it set while you try things. Always use `dbt build`, never `dbt run` then
`dbt test`: `build` skips what sits downstream of a failed test, so bad data
never reaches gold.

Two warnings are expected: 6 products have no name, and 15 order lines round to
0.00.

In **L06** the dbt runner gets its Dockerfile here. In **L10** the PII-redaction
model joins it.
