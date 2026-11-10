# ADR-0009: Attribute cost with four resource labels

- **Status:** accepted
- **Date:** 2026-11-06 (accepted by Enzo on 2026-11-06)
- **Author:** Enzo Meret
- **Lesson:** L09

## Context

The four groups share one project, `data-engineering-i1`, and one budget. When
the bill rises, the question is whose resource caused it. The answer has to
come from the resource itself, because we cannot read the invoice or the
project-wide jobs (`JOBS_BY_PROJECT` is refused; the Billing API answered 403 on
6 Nov 2026). See [costs](../costs.md) for the convention and the ledger.

| Fact | Figure | Source |
|---|---|---|
| Our monthly cost, at list price | $0.0077 (storage), $0 billed for queries | [Ledger](../costs.md), 6 Nov 2026 |
| Resources to attribute | 6: the data bucket, 4 datasets, the state bucket | [infra](../infra.md) |
| Other groups in the project | Yes: the rule is to touch only resources starting with `g04`. How many, we do not know | `CLAUDE.md` |
| What Terraform can label | The bucket and the 4 datasets, through the `labels` argument | `infra/terraform/main.tf` |
| What labels cannot label | Charges made before the label; the bytes a query processes (they belong to the job) | [costs](../costs.md), "What this does not attribute" |
| Can we create a project | Not tried. The course gives us this one, and we have no billing rights | Course; the 403 on the Billing API, 6 Nov |

## Options considered

| Option | For | Against |
|---|---|---|
| **Labels** on each resource | Works inside a shared project; appears in billing reports and the export; set by Terraform and reviewed in a pull request | Forward only. Does not tag query jobs unless the job sets a label. A missing or mistyped label silently drops a resource out of the report |
| **One project per team** | The cleanest cut: the invoice, quotas and IAM are per project, and nothing can be missed | Not available to us: the course gives one project. In a company it costs more setup per team and makes shared data harder to reach |
| **Resource tags** (instead of labels) | Defined once at organisation or project level and inherited by the resources below; usable in IAM and organisation policy, so a rule can be enforced, not only reported; they reach billing | Need organisation-level setup and permissions we do not have (we cannot read the project's IAM policy). Not tried: we have no organisation-level rights that we know of. Labels are the only one of the two we can set |
| **Split the bill by hand** (by headcount or by usage in a spreadsheet) | No setup | Someone redoes it every month and it reflects a guess. Cannot say which resource caused a spike |

## Criteria

1. **Possible with our rights:** the course gives one project, and we cannot read the invoice.
2. **Attributes without a person remembering:** the label must come from code.
3. **Shows which resource, not only which team.**
4. **Honest about what it misses.**

| | Possible | From code | Resource-level | Misses |
|---|---|---|---|---|
| Labels | Yes | Yes (Terraform) | Yes | The past; query bytes unless the job is labelled |
| Project per team | Not offered | Yes | No: only team-level | Little |
| Resource tags | No: needs organisation-level rights | Yes, once set up | Yes | Nothing, if they could be set |
| By hand | Yes | No | No | Whatever the person guesses wrong |

## Decision

Label every resource with four keys, `group`, `environment`, `layer` and
`lesson`, from Terraform, and label query jobs later. Labels are what we can do
inside this project; they are not the best design.

## Consequences

**What becomes easier.** A billing report grouped by `group` or `layer` shows
where storage cost sits, and a pull request that adds a resource without labels
is visible in review. The labels are in the plan, so a reviewer sees them.

**What stays hard.**

- Nothing before 6 Nov 2026 is labelled, and query cost is not labelled at all
  until `warehouse/measure.py` and dbt set job labels. Not done.
- A label added by hand is invisible to `terraform plan` (the provider only
  compares the keys the code declares). A label removed by hand is caught.
- We have not seen a billing report cut by these labels, because we cannot read
  billing. The convention is untested end to end.

**With ten teams.** Labels still work, but only if the values are enforced:
ten teams will each invent `team`, `Team`, `group` and `grp`. Then the choice
changes:

- **One project per team** becomes the right answer, because the cost is cut by
  the project without anyone's discipline, and each team's quota and IAM is its
  own. It is what a company with ten teams would do, and what we would ask the
  course for.
- **Keep labels inside each project** for the layer and the lesson, and enforce
  the keys. Resource tags are the tool made for that (inherited, and usable in
  organisation policy), but need the organisation-level setup we lack. Short of
  that, a CI check on the `.tf` files could be added to the workflow in [`.github/workflows/terraform.yml`](../../.github/workflows/terraform.yml).
- **Splitting by hand does not scale:** ten teams means ten sets of guesses.
