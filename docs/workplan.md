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

## Still open from steps 2 to 4

Nothing waits for these, but the repository is graded on them.

**Jane**
- **Consumer fixes:**
  - The same columns and types in every file, as declared in
    `ingestion/clickstream_external.sql`. Today a batch without an order has no
    `order_id`, and a batch of only cart events writes `qty` as an integer.
  - Bigger files: not one file per quiet second. Files of 1 to 11 rows were
    seen on 5 November.
  - In the dead letter queue, `rejected_at` instead of `event_time`, which
    holds the time of the rejection.

**Enzo**
- Confirm ADR 0004, then set it to accepted.
- Take `projectReaders` and `projectWriters` off `g04_warehouse`, as on
  `g04_bronze_1`: anyone with Viewer on the project can read it today.

**Evaluna**
- Delete the old dataset `g04_bronze`: the dataset only. The bucket and its
  files stay.
- Write your role in the README team table.

**Till**
- Delete the old merged branches on GitHub. New ones delete themselves.

## Not in this plan

- The Exercise 2 PDFs: each of us writes them after the project work.
