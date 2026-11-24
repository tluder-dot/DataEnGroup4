# Albert's Marketplace data platform: Group 4

The data platform of **Albert's Marketplace**, a fictional European online shop
for beauty products. Built by Group 4 for the Data Engineering & Cloud
Infrastructure course (MSA-DAT09-02, Albert School).

**What it does.** Every night at 02:00 UTC, Airflow (in Docker, on one member's
laptop) copies seven tables of the shop's PostgreSQL database into Cloud
Storage as Parquet: orders, order lines, products, reviews and addresses. That
is bronze. A consumer that is always on adds the shop's click events from
Kafka. dbt then builds silver (clean, typed, tested) and gold (a star schema)
in BigQuery, and a failed test stops the run before gold changes. Passwords
and card numbers never leave the shop.

**Who it is for.** The company's analysts and revenue reports, who get one
revenue figure in SQL, and its ML team, who get units sold per product, country
and day. Both read gold, never bronze or silver.

**Start here:**
- [docs/architecture.md](docs/architecture.md): the diagram, what runs today,
  what is not done yet, and the ten decisions
- [docs/orchestration.md](docs/orchestration.md): how to run the whole
  pipeline with Airflow
- [Run the jobs on a new machine](#run-the-jobs-on-a-new-machine), below: one
  job at a time

## Team

| Name | GitHub | Role |
|---|---|---|
| Till Lüder | [@tluder-dot](https://github.com/tluder-dot) | Coordination and setup. Step 2: bronze, the data dictionary, ADRs 0001 and 0002. The extractor. Step 5: dbt silver and gold, ADR 0005. The architecture page, every step |
| Evaluna Barth | [@evalunab](https://github.com/evalunab) | Step 10: governance (data classification, access, PII protection, erasure runbook, ADR 0010). Step 11: coordinates the video and pitch. Merges Enzo's PRs |
| Jane Galthie | [@jgalthie-sketch](https://github.com/jgalthie-sketch) | Step 3: the clickstream consumer, its schema and dead letter queue, failure modes, ADR 0003. Steps 6 and 7: the images and the DAG, ADRs 0006 and 0007 |
| Enzo Meret | [@emeret-as](https://github.com/emeret-as) | Step 4: native BigQuery tables, partitioning and clustering, daily demand materialised view, cost cap, slow-query runbook, ADR 0004 |

## How this repo grows

| Lesson | What your group adds | Where |
|---|---|---|
| L01 · Architecture decision frame | Data-flow matrix, first ADR, architecture diagram v1, star schema sketch | `docs/` |
| L02 · Object storage foundations | Bronze layer on Cloud Storage, data dictionary v1 | `docs/` |
| L03 · Batch, streaming, CDC | Ingestion pipelines | `ingestion/` |
| L04 · SQL warehouses | Warehouse tables, three costed queries | `docs/` |
| L05 · dbt and the medallion pattern | Silver and gold models, tests | `transform/` |
| L06 · Packaging data jobs | Dockerfiles for the ingestion job and dbt | `ingestion/`, `transform/` |
| L07 · Airflow | A scheduled DAG | `orchestration/` |
| L08 · Terraform | The platform as code, `terraform plan` in CI | `infra/`, `.github/workflows/` |
| L09 · FinOps | Labels, a budget alert, one measured optimisation | `infra/`, `docs/` |
| L10 · Security and governance | Least-privilege access, PII redaction, data classification | `infra/`, `transform/`, `docs/` |

Starter files for later lessons arrive as **pull requests** opened by the
teaching team. Review and merge them like any other change.

## How we work

**Start with [CONTRIBUTING.md](CONTRIBUTING.md)** (machine setup, names of our
shared resources, branch and review rules) **and
[docs/workplan.md](docs/workplan.md)** (who did what in steps 5 to 11).

- **Every change goes through a pull request,** reviewed by another member
  before it reaches `main`.
- **One decision, one ADR** in `docs/adr/`. Every member writes at least one. At
  the oral defence, each of you defends a technical choice unprepared.
- **The commit history is graded.** Commit in small steps, with messages that
  say why.
- **Never commit secrets:** no `.env` files, no service-account keys.
  `.gitignore` blocks the usual names; it cannot catch everything.
- **Keep `docs/architecture.md` current.** It is the diagram you present at the
  defence.

## Run the jobs on a new machine

You need Docker, and for anything that reads or writes BigQuery or the bucket,
your own Google login: `gcloud auth application-default login`. The images
run on Intel and Apple machines alike. Tags are listed in
[ADR 0006](docs/adr/0006-image-registry-and-tags.md).

```
TAG=20261118-796cf3e
ADC="$HOME/.config/gcloud/application_default_credentials.json"

# The dbt runner: check the connection, in your own dataset
docker run --rm -v "$ADC":/gcloud/adc.json:ro \
  -e GOOGLE_APPLICATION_CREDENTIALS=/gcloud/adc.json -e DBT_DATASET=sandbox_<initials> \
  docker.io/jgalthie/group4-transform:$TAG debug --connection

# The extractor, one table, into a local folder (needs the albert-marketplace stack)
docker run --rm --network albert-marketplace_default \
  -e DATABASE_URL=postgresql://postgres:postgres@db:5432/marketplace \
  -e TABLE=product -e OUT=/data -v "$PWD/out":/data \
  docker.io/jgalthie/group4-ingestion:$TAG
```

On Windows, write the paths as `C:/Users/<you>/...`. The full check, image
deleted and pulled again, is in [docs/reproduce.md](docs/reproduce.md).

**Tested on a machine from another group:** not yet.

## Layout

```
docs/
  architecture.md    the diagram, what exists now, the decisions
  data-flows.md      data-flow matrix
  adr/               architecture decision records
  model/             dimensional model sketches
  runbooks/          slow query, failed run, erasure
  evidence/          outputs that back a claim in the docs
  queries/           the daily revenue report
ingestion/           export landing, extractor, clickstream consumer (L03)
warehouse/           native tables and daily demand views (L04)
transform/           dbt: silver and gold (L05)
orchestration/       Airflow DAG (L07)
infra/               lifecycle and access (L02), Terraform (L08),
                     governance scripts (L10)
```

## Data

The source system is Albert's Marketplace's company repo (link on the course
site). Its data is synthetic or derived from public datasets; its licence and
attribution are stated there.

## Ownership

**No licence is granted for this repository.**
- **The template:** this README, the `docs/` templates and the folder structure
  remain the course author's intellectual property. Do not reuse them outside
  the course.
- **Your work:** what your group writes here belongs to your group.
