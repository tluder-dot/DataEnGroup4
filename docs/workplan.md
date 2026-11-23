# Work plan: steps 5 to 11

All sessions have taken place. What is left is project steps 5 to 11 and the
defence. The deliverables and "done when" lines are in the course brief, under
each lesson's "Project step". This page says who does what.

How to work (setup, names, review rules): [CONTRIBUTING.md](../CONTRIBUTING.md).

**No service accounts, so full batch.** Charles told us (29 October) that
groups get no service accounts in this project. Without one, Airbyte cannot
reach our bucket or BigQuery, so the database tables reach bronze through our
own extractor, with full batch as its main mode.

## Who owns what

| Part | Member | Steps | ADRs | PRs merged by |
|---|---|---|---|---|
| 1 | **Till** | 5: dbt silver, gold and tests | 0005 materialisations | Jane |
| 2 | **Jane** | 6: images. 7: Airflow | 0006 image tags, 0007 idempotency | Enzo |
| 3 | **Enzo** | 8: Terraform. 9: FinOps | 0008 remote state, 0009 cost attribution | Evaluna |
| 4 | **Evaluna** | 10: governance. 11: ready to defend | 0010 data classification | Till |

- **Each member does their steps end to end.**
- **The next person in line reads the PR and merges it,** because their part
  builds on it. Nobody merges their own PR.
- **`docs/architecture.md`:** Till updates the diagram for every step. Tell him
  what changed when your PR is up.
- **Step 11 is for all four:** each member claims two ADRs and speaks in the
  video. Evaluna coordinates.

## Who can start when

| When | Who | What |
|---|---|---|
| **Now** | Till | Step 5, starting with the `transform/` skeleton |
| **Now** | Jane | Step 6: `.dockerignore` and the ingestion image |
| **Now** | Enzo | Step 8, then step 9 |
| **Now** | Evaluna | Step 10: classification, access matrix, ADR 0010 |
| **After step 5** | Jane | The dbt image, then the DAG (step 7) |
| **After step 5** | Evaluna | The erasure runbook: it has to run through silver and gold |
| **After step 9** | Evaluna | Enforcement in Terraform, on top of the labels |
| **Last** | Everyone | Step 11: the video needs the DAG running |

## Limits to check, not assume

- **Step 7:** Airflow is 7 containers and about 5.7 GB of images on disk. The
  brief gives no memory figure, so try it early, with the company stack running
  beside it. Without a service account, jobs run with the runner's own `gcloud`
  login, mounted read-only into local containers, as in the L05 and L07 labs.
- **Step 8:** a service account cannot be declared, and project-level bindings
  are not allowed. Write the gap in `docs/infra.md`. Enzo is an owner of
  `g04_bronze_1`, so that his Terraform can manage it.
- **Step 9:** our logins may not reach budgets or the billing export.
  `JOBS_BY_PROJECT` is refused; use `JOBS_BY_USER`, and say so.
- **Step 10:** creating policy tags may be refused. The brief asks for gaps to be
  written down.

## Open items from steps 2 to 4: all closed

Checked on 23 November 2026.

- **Jane:** the consumer writes the same columns and types in every file, files
  of up to 200 rows or every 15 minutes, and `rejected_at` in the dead letter
  queue (#39, 6 November).
- **Enzo:** ADR 0004 is accepted. `g04_warehouse` no longer grants the
  project's readers and writers.
- **Evaluna:** the old `g04_bronze` dataset is deleted, and her role is in the
  README.
- **Till:** the old merged branches are deleted (8 November). His dev datasets
  `l05_tl_silver` and `l05_tl_gold` are deleted too (23 November).

## Not in this plan

- The Exercise 2 PDFs: each of us writes them after the project work.
