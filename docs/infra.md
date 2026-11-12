# Infrastructure as code

What the group's cloud project holds, what Terraform manages, what it cannot,
and how the state is kept. Everything here was checked on 6 November 2026
against project `data-engineering-i1`, region `europe-west1`.

Code: [`infra/terraform/`](../infra/terraform/). Decision on where the state
lives: [ADR 0008](adr/0008-remote-state.md).

## Resources

| Resource | Why it exists | Made by hand? |
|---|---|---|
| `gs://data-engineering-i1-g04` (bucket `data`) | Bronze files and the lifecycle rules (step 2) | Created by hand in L02. **Adopted** with an `import` block on 6 Nov 2026; Terraform now owns it |
| `g04_bronze_1` | External tables over the bronze files (step 2) | Created by hand. **Adopted** |
| `g04_silver` | dbt silver models (step 5) | Created by hand on 6 Nov. **Adopted** |
| `g04_gold` | dbt gold models (step 5) | Created by hand on 6 Nov. **Adopted** |
| `g04_warehouse` | Native tables and materialised views of step 4 | Created by hand. **Adopted** |
| `gs://data-engineering-i1-g04-tfstate` | Holds the Terraform state, versioned | **By hand, on purpose, and not in Terraform** (see below) |
| `g04_bronze` | The first bronze dataset, replaced by `g04_bronze_1` | By hand. **Not adopted**: Evaluna deletes it, so declaring it would only add something to delete |
| L2 service account | Would run the pipeline without a personal login | **Does not exist.** Not handled, see [Gaps](#gaps) |

The tables and views inside the datasets are not in Terraform. They are built
by `warehouse/*.sql` (step 4) and by dbt (`transform/`). Terraform owns the
containers; the SQL and dbt own what is in them.

## The state bucket

It cannot be managed by the state it holds: if Terraform destroyed it, it would
destroy its own record. So it was made by hand, once, on 6 November 2026:

```
gcloud storage buckets create gs://data-engineering-i1-g04-tfstate \
  --project=data-engineering-i1 --location=europe-west1 \
  --uniform-bucket-level-access --public-access-prevention
gcloud storage buckets update gs://data-engineering-i1-g04-tfstate --versioning
gcloud storage buckets update gs://data-engineering-i1-g04-tfstate \
  --update-labels=group=g04,layer=tfstate
```

(The gcloud CLI is not installed on the laptop that ran this; the same settings
were applied with the Python Storage client. The commands above are the
equivalent.)

Read back on 6 Nov 2026: location `EUROPE-WEST1`, versioning on, uniform access,
public access prevention enforced, soft delete 604800 s, labels
`group=g04, layer=tfstate`.

**Who can read it.** Only the three bindings Cloud Storage gives every new
bucket: `projectOwner` and `projectEditor` (bucket and object owner),
`projectViewer` (bucket and object reader). We added none. That means anyone
with Viewer on the course project can read the state, and the state holds the
dataset access lists (names of people). We cannot list who holds Viewer
(`gcloud projects get-iam-policy` is refused), so we do not know how many
people that is. See [ADR 0008](adr/0008-remote-state.md).

**Locking.** The `gcs` backend writes `platform/default.tflock` while a plan or
apply runs, so two of us cannot apply at once.

## What was done, in order

1. `terraform init` against the `gcs` backend (prefix `platform`). Provider
   resolved to `hashicorp/google 8.10.0`, which satisfies `~> 8.4`.
2. First plan, before any `import`: **5 to add**. Terraform did not know the
   resources existed and would have tried to create them.
3. Added the five `import` blocks ([`imports.tf`](../infra/terraform/imports.tf)).
   Plan: **5 to import, 0 to add, 4 to change, 0 to destroy**. The 4 changes
   were the datasets' `description`, which was set by hand and not yet in the
   code: Terraform wanted to set it to null.
4. Declared the four descriptions as they really are. Plan: **5 to import,
   0 to add, 0 to change, 0 to destroy**. Nothing is created, changed or
   destroyed in the cloud by this apply; it only writes the state.
5. `terraform apply`: **5 imported, 0 added, 0 changed, 0 destroyed.**
6. `terraform plan`: **"No changes. Your infrastructure matches the
   configuration."**

Checks on 6 Nov 2026:

- `terraform state list` shows the 5 resources.
- The state is in the bucket: `platform/default.tfstate`, 21 225 bytes.
- `git log -- infra/terraform/terraform.tfstate` prints nothing: no state file
  was ever committed. `.gitignore` covers `*.tfstate*`, `.terraform/` and
  `*.tfvars`; `.terraform.lock.hcl` is committed.

The `import` blocks stay in the code as the record of what was adopted and from
which id. They do nothing once the resource is in the state.

## Drift

**Change made outside Terraform.** On 6 Nov 2026 at about 14:40 UTC, the
`description` of `g04_warehouse` was changed through the BigQuery API instead
of the code, to "Group 4: native tables for step 4 (L04), edited in the
console".

**Plan output** (saved in
[`evidence/infra-drift-plan.txt`](evidence/infra-drift-plan.txt)):

```
  # google_bigquery_dataset.warehouse will be updated in-place
  ~ resource "google_bigquery_dataset" "warehouse" {
      ~ description = "Group 4: native tables for step 4 (L04), edited in the console" -> "Group 4: native tables for step 4 (L04)"
    }
Plan: 0 to add, 1 to change, 0 to destroy.
```

**What we chose: overwrite.** `terraform apply` put the description back to
the one in the code. Then `terraform plan` said "No changes".

Why: the description in the code is the one the group agreed on, and the edit
was not recorded anywhere (no pull request, no reviewer). A change nobody
reviewed should not become the truth because it happened first.

**If it had been an incident fix, we would adopt instead.** Say a teammate
changed a setting by hand at night to stop an outage. Overwriting would undo the
fix at the next apply and bring the outage back. So: leave the cloud as it is,
open a pull request that changes the code to match, have it reviewed, and only
then apply (which then shows "No changes"). The rule: during an incident the
cloud is right and the code catches up; outside one, the code is right and the
cloud is put back.

**One drift Terraform did not see.** Before that, we added a label
`edited_by=hand` to the data bucket by hand. The plan said "No changes". The
`labels` argument of the Google provider is non-authoritative: it only compares
the labels the code declares, so an extra label outside the code is invisible.
(This plan output was not saved; the label was removed again at 14:40 UTC.) The
same will apply to the labels of step 9 ([costs](costs.md)): a label added by
hand is not detected, a declared label changed by hand is.

## CI

[`.github/workflows/terraform.yml`](../.github/workflows/terraform.yml) runs on
every pull request that touches `infra/`:

```
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
```

It has no credentials, so there is **no plan in CI**. The plan runs on the
author's laptop, and the reviewer asks to see its output in the pull request. A
plan in CI would need a service account key or workload identity, and groups get
no service account here.

## Gaps

- **No service account.** The brief asks for an L2 service account. Groups
  cannot create one in this project (Charles), so there is nothing to declare.
  Every job runs as a personal login. We did not try a
  `google_service_account` block: Charles told us groups get none.
- **No project-level bindings.** We cannot read or change the project's IAM
  policy, so `google_project_iam_*` cannot be used. Resource-level IAM
  (`google_storage_bucket_iam_member`, `google_bigquery_dataset_iam_member`)
  is allowed and is the only kind we could declare.
- **Dataset and bucket IAM is not in Terraform yet.** The bindings are in
  [`infra/iam.md`](../infra/iam.md), applied by hand. They were not adopted
  here because `google_bigquery_dataset_iam_binding`/`_policy` are
  authoritative and would replace the existing list; `_member` is additive but
  would still need one block per person. Not done, because the risk is removing
  our own access to datasets we cannot recreate.
- **Enzo's reach is four datasets and the data bucket.** Enzo is OWNER of
  `g04_warehouse`, `g04_silver`, `g04_gold` and `g04_bronze_1`, which is why
  Terraform run by him can manage them.
- **The state is readable by every project Viewer** (above).
- **Tool versions are only loosely pinned.** The lock file pins the provider
  (8.10.0); `required_version = ">= 1.9"` sets a minimum for Terraform itself,
  not a maximum. CI and the laptop that did the adoption both run 1.17.1.
