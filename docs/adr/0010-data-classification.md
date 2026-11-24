# ADR-0010: Grant access by data class, enforced at the lowest layer that can carry it

- **Status:** accepted (2026-11-24)
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
| Result of the test by a second login | **Not refused.** Till ran the same test with his own login on 23 Nov 2026: the read of the tagged column returned 3 rows, 3 seconds after the tag, and the tag's IAM policy was empty. Two of our four logins read a column that nobody is granted; Jane's and Enzo's were not tested. We do not know which role lets him through, so the refusal is still not shown | [governance](../governance.md) and `infra/governance/policy_tag_test.py`, 23 Nov 2026 |
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

## Decision

We grant access by the **class of the column**, and apply the rule at the **lowest
layer that can carry it**: a policy tag where the table is native, a hashed
identifier where the layer is views, and no identifier at all in gold. The classes
and the access matrix are the policy; the enforcement is what the platform lets us
build. Not everything below is in place:

| Element | State |
|---|---|
| The seven classes, an owner and a reason for each of the 323 columns | **In place**, merged ([governance](../governance.md)) |
| The access matrix by role and class, and its 12 gaps | **Proposed**: pull request in review |
| Gold holds no identifier | **In place**: no `buyer_id` column in gold, checked 19 Nov. Its order lines still carry an `order_id` that leads to a person until gold is rebuilt |
| The buyer ID hashed in silver, the salt in its own dataset | **Tested and merged, waiting for deployment.** `g04_secrets` exists: Enzo created it with Terraform on 23 Nov 2026 at 13:27 UTC, from `infra/secrets-dataset`. The salt was written on 23 Nov at 14:02 UTC: one row of 64 hex characters, its value shown nowhere. The pull request `transform/pii-redaction` was merged on 24 Nov at 09:06:42 UTC (#58). **The DAG still runs the old image tag** (`20261118-796cf3e`), so silver keeps the real `buyer_id` until Jane sets a new tag of the transform image and a run succeeds: until then the nightly run rebuilds silver from the old image, without the hash. The salt is in place, so the new tag can be set |
| Policy tags on the columns of native tables | **Tested on a 3-row copy, not applied to any real table.** The taxonomy was made by hand for the test and is deleted after it. Declaring it in Terraform (`google_data_catalog_taxonomy` and `google_data_catalog_policy_tag`) is **proposed**. Result with a second login: **not refused** (Till, 23 Nov 2026). The refusal is still not shown, and stays a gap. |
| Narrower grants through Terraform, one `google_bigquery_dataset_iam_member` per grant | **Proposed**: Jane's `dataViewer` to `metadataViewer` on `g04_warehouse`, put to Enzo and Jane on 19 Nov. Jane agreed on 20 Nov. **Not applied on purpose, pending a test by Jane** (#69, Enzo, 23 Nov): it is worth applying only if a read of `g04_warehouse` as Jane is refused after the change; if she can still read, it is cosmetic, because a project-level role that we cannot list gives the same rows (gap 10) |
| Evaluna's Writer to Reader on `g04_silver` and `g04_gold` | **In place**, applied by `bq update` and not by Terraform, on 20 Nov 2026 (11:49:48 and 11:50:05 UTC). It narrows the lists of the datasets, not what her login can do: a project-level role gave the same permissions before and after (gap 10) |

## Consequences

**What becomes easier.** A new column gets a class by rule, and the class says who
may read it. A reader asks one file which columns are personal and who owns them.
Silver no longer carries the real buyer ID once the hash is deployed, so the people
who read silver stop being the people who could find a buyer.

**What becomes harder.** Two levels of grants, a dataset and a tag, have to be
reasoned about together. `stg_orders` and `stg_customer_shipping` become tables
instead of views: a view would store the salt in its SQL, or oblige every reader of
silver to read the salt table. That departs from ADR-0005 for those two models.
ADR-0005 is accepted and is not rewritten here; its status line should say "partly
superseded by ADR-0010", which is Till's file, so it is asked in the pull request.

**The rule is stronger on paper than in the platform.** The policy classifies every
column, but nothing in the platform shows a refusal yet. A tag set on a test column
did not refuse a read by our login, and a project-level role that we cannot list
reads tables that the dataset grants do not name. What protects the buyer today is
what we removed from the data, not what we blocked. The hash, and a gold without an
identifier, hold wherever a role is wider than it should be.

**The salt lives in one place.** It is the table `g04_secrets.pii_salt`: it was
generated in memory and written nowhere else, so it cannot leak from a file. The cost
is that if it is lost or replaced, every hash changes at the next build, and nobody can
compute the old ones again. Silver stays consistent, because it is rebuilt in full every
night and both hashed tables use the salt of the same run. An erasure starts from the
real identifier, found in bronze, so it does not depend on the salt; only the check of
the hashed silver does, with the salt of the day. The script that writes the salt
refuses to replace an existing one without `--rotate`.

**Retention.** The runbook leaves this to this ADR. We keep 7 days of soft delete in
the bucket and 168 h of time travel on the four datasets. The soft delete is the
only safety net if a rewrite of production files goes wrong, and the first real one
will have none other. A person erased today stays in the old versions for 7 days,
and in BigQuery for 168 h plus a fail-safe period that we cannot read. We found no
way to purge soft-deleted objects early. **Open question: whether that delay is
acceptable to the person and to the law.** We did not answer it. The trigger: at the
first real request, the reply says "the copies are deleted within 7 days", and the
question is put to someone who can answer it.

**What would change our mind.**
- **A second test, by a login that does not hold `fineGrainedGet`, is not refused
  either:** the tags enforce nothing here. We drop them, and new sensitive columns
  go in a dataset of their own (option 3).
- **The project's IAM policy becomes readable and the broad role is removed:** we
  repeat the tests and the reduction of Jane's grant, since the dataset grants would
  then bind.
- **A consumer needs a shape that no class gives,** for example part of a free-text
  column: a view for that consumer (option 2) costs less than a new class.
- **Native tables with a personal column that carry a tag:** 0 of 5 today
  (`orders_month`, `orders_plain`, `review`, `customer_shipping`, `shipping_details`).
  If it is still 0 when the platform changes, the enforcement is a claim.

**Not handled.** Free text (`unclassified`), because we cannot tell what it holds.
The company's database, which restores an erased person every night. The salt, which
is only as secret as the dataset that holds it. The copies of an erased person that
survive 7 days.
