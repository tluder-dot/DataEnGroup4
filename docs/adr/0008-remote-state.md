# ADR-0008: Keep the Terraform state in a versioned Cloud Storage bucket

- **Status:** proposed (Enzo to confirm or change the decision before review)
- **Date:** 2026-11-06
- **Author:** Enzo Meret
- **Lesson:** L08

## Context

Terraform keeps a record, the state, of which real resource each block in the
code stands for. Without it, it cannot tell "already exists" from "to create".
Where that file lives decides who can apply, who can read it, and what a lost
file costs. See [infra](../infra.md) for the resources.

| Fact | Figure | Source |
|---|---|---|
| Resources in the state | 5: the data bucket and 4 datasets | `terraform state list`, 6 Nov 2026 |
| Size of the state | 21 225 bytes | `platform/default.tfstate` in the state bucket, 6 Nov |
| People who run Terraform | 1 now (Enzo owns the datasets); Till and Evaluna could | [Work plan](../workplan.md) |
| Service account for CI | None. Groups get none in this project | Charles; [iam](../../infra/iam.md) |
| Who can read the state bucket | `projectOwner`, `projectEditor`, `projectViewer` and nobody else; we cannot list who holds Viewer | Bucket IAM policy read 6 Nov (`gcloud projects get-iam-policy` is refused) |
| Bucket settings | `EUROPE-WEST1`, versioning on, uniform access, public access prevention enforced | Storage API, 6 Nov |

The state holds what Terraform reads back from the cloud: dataset access lists
with the logins of the four of us, labels, descriptions. It holds no secret:
there is no key, password or service account in this configuration.

## Options considered

| Option | For | Against |
|---|---|---|
| Local state (`terraform.tfstate` on a laptop) | Nothing to set up | One person only: a second laptop would plan "5 to add". Lost with the laptop. Easy to commit by mistake, and a committed state lives in git history forever |
| Cloud Storage bucket, versioned (`gcs` backend) | Shared; locks while someone applies; every write keeps the previous version; no new account or tool; same project and IAM as everything else | Made by hand once (it cannot hold its own state). Readable by every project Viewer. Costs a few cents of storage |
| Terraform Cloud | Hosted locking, history and run logs; its own access list instead of the project's | A new account and a token for each of us; it would run with credentials we cannot give it (no service account). Not available in the course project |

## Criteria

1. **Shared, with locking:** a second person must be able to plan and apply
   without a "5 to add".
2. **Recoverable:** a bad write or a deletion must be undoable.
3. **Access:** who can read it, given it lists our logins.
4. **Fits what we are allowed:** no service account, no project-level IAM.
5. **Cost and setup.**

| | Shared + lock | Recoverable | Access | Fits our limits | Cost / setup |
|---|---|---|---|---|---|
| Local | No | No | Laptop owner | Yes | None |
| GCS, versioned | Yes | Yes | Every project Viewer (too wide) | Yes | One bucket |
| Terraform Cloud | Yes | Yes | Own list | No: needs an account and token the course does not provide | Highest |

## Decision

Keep the state in a versioned bucket in the course project,
`gs://data-engineering-i1-g04-tfstate`, prefix `platform`, made by hand and not
managed by Terraform.

## Consequences

**Who can read it.** Every principal with Viewer on the course project, through
the bucket's default `projectViewer` binding. That is wider than the four of us,
and we cannot say how many people it is. We did not narrow it: removing
`projectViewer` might also cut off our own reads, as with the data bucket
([iam](../../infra/iam.md), "Not handled"). L10 should revisit it. What leaks is
dataset access lists, labels and descriptions, not secrets.

**If the state file is deleted.** The cloud resources stay (Terraform only
destroys what a plan tells it to). But Terraform no longer knows they exist, so
the next `plan` says "5 to add", and an `apply` would fail with "already
exists" on every one, or worse, create duplicates where names are generated.
The resources are orphaned from the code until each is imported again with the
`import` blocks that are still in `infra/terraform/imports.tf`. That is why
they stay in the repo.

Because the bucket is versioned, a deleted or overwritten `default.tfstate` can
be restored from its previous generation (`gcloud storage cp
gs://…/platform/default.tfstate#<generation> …`) without importing anything.
We did not test a restore. Soft delete (7 days) is a second net for the same
file.

**If the whole state bucket is deleted.** Versions go with it unless soft
delete still holds them (7 days). After that, only the imports remain.

**What gets harder.** The state bucket is the one thing outside the code. It is
rebuilt only from the commands in [infra](../infra.md). Nothing detects a drift
on it.

**What to watch.** A second applier with a different Terraform version can
upgrade the state format for everyone. The lock file pins the provider, not the
Terraform binary.
