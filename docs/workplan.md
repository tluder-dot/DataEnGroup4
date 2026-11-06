# Work plan until session 5

**Goal:** project steps 1 to 4 done, reviewed and merged before session 5.
The deliverables and "done when" lines below come from the course brief.

How to work (setup, names, review rules): [CONTRIBUTING.md](../CONTRIBUTING.md).

**No service accounts, so full batch.** Charles told us (29 October) that
groups get no service accounts in this project. Without one, Airbyte cannot
reach our bucket or BigQuery, so the database tables reach bronze through our
own extractor, with full batch as its main mode. The next session shows a
workaround with Airflow.

## Who owns what

| Member | Owns | ADR | PRs reviewed by |
|---|---|---|---|
| **Till** | Steps 1 and 2, the extractor, data dictionary, `docs/architecture.md` | 0001, 0002 | Jane |
| **Jane** | Step 3: the clickstream consumer, its schema and dead letter queue, failure modes | 0003 | Till |
| **Enzo** | Step 4: native tables, tuning, materialised view, cost cap, runbook | 0004 | Jane |
| **Evaluna** | Tasks from session 5 on | | |

- **Step 2 moved from Evaluna to Till on 3 November.** Evaluna wrote the
  landing script (#10); her next tasks come with the later steps.
- **For now, Jane approves and merges Till's PRs.** For every other PR, the
  reviewer approves and the author merges.
- **A review says what was checked,** and comes before the merge.
- At the defence, everyone is asked about an ADR they did not write.

## Where each step stands

**Step 1:** done (#2 to #5, #7, #8).

**Step 2:** merged (#12 to #18), but none of these PRs has a submitted review.

**Step 3:**

| Deliverable | What | PR |
|---|---|---|
| 1 | Connector: dropped. Without a service account, Airbyte cannot reach our bucket or BigQuery (ADR 0003). The extractor carries the seven tables instead | |
| 2 | `ingestion/extract_orders.py` | #32 |
| 3 to 5 | `ingestion/consume_clickstream.py`, `clickstream.schema.json`, `bronze/_dlq/` | #21 |
| 6 | `docs/ingestion-failure-modes.md` | #23, #32 |
| 7 | ADR 0003 | #24, #32 |
| 8 | The clickstream in the data dictionary | #22, #32 |
| 9 | `docs/architecture.md` | #33 |

*Not met:* "three paths write without a human". A person starts each path until
L07.

**Step 4:** in #25 to #30, for Jane's review.

## Still to do

**Jane**
- Review and merge this plan's PR first, then #32. #33 comes last, after #27
  and #28: it links to them.
- Review Enzo's #25 to #31.
- Submit a review on #12 and #14, even after the merge: step 2 needs at least
  one reviewed PR.
- **J7 · Consumer fixes** (nothing waits for them):
  - The same columns and types in every file, as declared in
    `ingestion/clickstream_external.sql`. Today a batch without an order has no
    `order_id`, and a batch of only cart events writes `qty` as an integer.
  - Bigger files: not one file per quiet second. Files of 1 to 11 rows were
    seen on 5 November.
  - In the dead letter queue, `rejected_at` instead of `event_time`, which
    holds the time of the rejection.

**Enzo**
- Merge #25 to #31 after Jane's approval: #25 and #26 first.
- Confirm ADR 0004, then set it to accepted.
- Take `projectReaders` and `projectWriters` off `g04_warehouse`, as on
  `g04_bronze_1`: anyone with Viewer on the project can read it today.

**Evaluna**
- Delete the old dataset `g04_bronze`: the dataset only. The bucket and its
  files stay.
- Write your role in the README team table.

**Till**
- Review Jane's J7 PR.

## Enzo: step 4, the warehouse

Bronze is in `g04_bronze_1`, readable by Enzo. Before any measurement, turn the
query cache off. Record **bytes processed**, never bytes billed:
billing has a 10 MiB minimum.

**N1 · The working set as native tables:** dataset `g04_warehouse`
(deliverable 1).
- Load the seven tables. `order_items` joins `orders` to get `order_date`.
- Say which tables you loaded and which stay external, and why.

**N2 · Tuning:** `docs/warehouse-tuning.md` (deliverables 2, 4 and 7).
- A table: table, change, query, bytes before, bytes after, ratio.
- Partition by a defended grain: three years of orders suggest month.
  Cluster where a query filters. Report the changes that bought nothing
  (1.0×) too, each with a sentence.
- Three analytical queries the project needs: SQL, bytes processed, cost at
  $7.50 per TiB, tuned versus untuned.
- `maximum_bytes_billed`: where it is set, the value and why, and the exact
  error it gives.

**N3 · Daily demand materialised view:** `warehouse/daily_demand.sql`
(deliverable 3), plus the collapse ratio, order lines ÷ distinct (product,
day), in N2's document. At about 1.14 the view saves no bytes under
per-byte billing. Keep it and say what it costs, or show a coarser grain that
moves the ratio.

**N4 · ADR 0004:** `docs/adr/0004-warehouse-pricing.md` (deliverable 5).
- On demand or capacity: the workload in numbers, and the crossover
  arithmetic.
- The decision and its cost.
- What would change your mind, as a number someone can watch.

**N5 · Runbook:** `docs/runbooks/slow-query.md` (deliverable 6).
- "A 2-second query now takes 2 minutes", written for a teammate at 23:00.
- Ordered steps, where to click, and when to escalate.
- It covers: lost partition filter, table outgrew its grain, one stage
  dominates, skew, data changed shape, cached comparison.

**N6 · Costs:** add the warehouse section to `docs/costs.md`, after #16 is
merged.

## Everyone, alone, before session 5: the L05 setup

About 20 minutes; the course's "Before the session: Docker and dbt" page.

1. Start Docker Desktop.
2. `docker pull charlestng/dbt-bigquery:1.12.1`
3. `gcloud auth application-default login`
4. In a folder outside this repo (`~/de/l05`), write `profiles.yml`
   (project `data-engineering-i1`, dataset `l05_<your initials>`, location
   `europe-west1`) and `dbt_project.yml`.
5. Run `dbt debug` in the container until it prints **All checks passed!**

The seven tables the setup checks for are `g04_bronze_1`'s external tables.

## Not in this plan

- The Exercise 2 PDFs: each of us writes them after the project work.
- Till's L02 Exercise 1 page (PR #6).
