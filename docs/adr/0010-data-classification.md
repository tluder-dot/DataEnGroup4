# ADR-0010: Grant access by data class, enforced at the lowest layer that can carry it

- **Status:** proposed (the group accepts it by reviewing the pull request)
- **Date:** 2026-11-20
- **Author:** Evaluna Barth
- **Lesson:** L10
- **Relates to:** partly supersedes [ADR-0005](0005-materialisations.md), for two
  staging models (see Consequences)

## Context

The platform holds personal data in three layers, and the people who read it are
the four of us, a pipeline that runs with one of our logins, and, one day, an
analyst. The question is why access should follow the class of a column, rather
than a simpler rule. Each figure below says where it comes from.

| Fact | Figure | Source |
|---|---|---|
| Columns with a class and an owner | 323 in 7 classes: bronze 176, silver 60, gold 31, warehouse 56. Free text is `unclassified` | [governance](../governance.md), metadata read 19 Nov 2026 |
| Where an identifier sits | `buyer_id` in 7 silver views. An identifier column in 5 native tables of the warehouse. In no gold column | [governance](../governance.md), 19 Nov |
| What can carry a policy tag | "BigQuery only supports column-level access control for BigLake tables, BigQuery tables, and BigQuery Omni tables." Our bronze tables are 35 plain external tables, and silver is 13 views and 1 table ([ADR-0005](0005-materialisations.md)) | BigQuery documentation, read 19 Nov; `INFORMATION_SCHEMA`, 19 Nov |
| A tag on a test column | Taxonomy and 5 tags created 20 Nov at 09:34 and 09:38 UTC. A tag set on `buyer_id` of a 3-row synthetic table at 09:39:27. Reading that column at 09:39:39 and at 09:50:06 returned the 3 rows. The tag's IAM policy is empty and the taxonomy enforces fine-grained access | Tests of 20 Nov 2026 |
| Result of the test by a second login | **Not obtained: no second login ran the test by 20 Nov 2026. Documented as a gap; the refusal is not shown.** | Test of 20 Nov 2026 |
| What our logins hold | `bigquery.tables.getData` on `g04_warehouse.orders_month`, where the dataset lists no grant for this login. `datacatalog.categories.fineGrainedGet` at project level. The project's IAM policy is refused | `testIamPermissions`, 19 Nov |
| Who can tell who read what | The `data_access` log has no BigQuery entry over 30 days. `INFORMATION_SCHEMA.JOBS_BY_PROJECT` can be read | Cloud Logging and BigQuery, 19 Nov |
| A hashed buyer ID in silver | On a test target: `PASS=81 WARN=3 ERROR=0`; gold gives 115,175 orders and EUR 20,261,896.25, the production figures to the cent; 0 of 100,046 hashed IDs equal a real one | [pseudonymisation test](../evidence/pii-redaction-test.md), 19 Nov |
| Authorized views and Terraform | The IAM resources "will remove any authorized view permissions from the dataset" | Provider documentation, read 19 Nov |
| Gaps between the access matrix and the real grants | 12 | [governance](../governance.md), 19 Nov |
| What survives an erasure | 7 days of soft delete in the bucket (604,800 s) and 168 h of time travel on the four datasets. The test left 42 object versions, 250,019,612 bytes | [erasure test](../evidence/erasure-test.md), `gcloud` and `bq show`, 20 Nov |

## Options considered

| Option | Buys you | Costs you |
|---|---|---|
| **Classify columns, grant on the class** (ours) | One rule survives a new table. Auditable: the policy is a file | Two levels of grants to reason about (dataset and tag). **A tag that is misconfigured protects nothing and says nothing.** We set one and the read was not refused. It cannot go on a view or an external table |
| **A view per consumer** | Exactly the right shape, no tagging | A view to maintain per consumer, forever. Authorized views and the Terraform IAM resources work against each other. A project-level role still reads the tables under the view |
| **A dataset per sensitivity level** | Simple, coarse, hard to get wrong | The same data copied twice and two things to keep in step. We already split by layer, and a dataset grant is bypassed by a project-level role (`getData` on a table that the dataset does not list) |
| **Trust people not to query it** | Nothing to build | It is not a control. Here the audit could not even show it: the log that records data reads is empty |

## Criteria

1. **Possible with our rights:** no service account, no read of the project's IAM
   policy.
2. **One rule survives a new table.**
3. **Verifiable:** the policy can be read, and the enforcement shown by a refusal
   or an audit.
4. **Fits the architecture:** silver in views, bronze in external tables, gold in
   tables, rebuilt by dbt.
5. **How it fails:** loudly, or in silence.

| | Possible | One rule | Verifiable | Fits | Fails |
|---|---|---|---|---|---|
| Classify and grant on the class | Yes: a taxonomy can be created | Yes, for the class; a tag is set per column | The policy, yes. A refusal, not shown | Partly: native tables only | In silence |
| A view per consumer | Yes | No: a view per consumer and table | The view, yes. The tables under it stay open to a project-level role | Yes, silver is already views | In silence, through the tables |
| A dataset per level | Yes | Partly: a new table goes to the right dataset | The grant, yes. Bypassed by a project-level role | Yes, we split by layer already | In silence, through the project role |
| Trust people | Yes | Not applicable | No: no record of reads | Yes | In silence |
