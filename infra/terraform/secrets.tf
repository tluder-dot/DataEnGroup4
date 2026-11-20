# The dataset that holds the salt of pseudonymise() (transform/seed_pii_salt.py).
# It holds no data of ours, only one secret, so it is its own dataset: dbt reads
# it with the runner's login, and nobody else needs it.

variable "secrets_owner" {
  description = "Who manages the dataset with Terraform. A login, set in terraform.tfvars (not committed)."
  type        = string
}

variable "secrets_writers" {
  description = "Logins that write the salt (seed_pii_salt.py). Set in terraform.tfvars."
  type        = list(string)
}

variable "secrets_readers" {
  description = "Logins that run dbt, so that read the salt. Set in terraform.tfvars."
  type        = list(string)
}

resource "google_bigquery_dataset" "secrets" {
  dataset_id  = "${var.group}_secrets"
  location    = var.region
  labels      = merge(local.base_labels, { layer = "secrets", lesson = "l10" })
  description = "Group 4: the salt of pseudonymise(). Not data. Read only by the dbt runner."

  # A new dataset, so a complete access list is safe here. It is declared in
  # full on purpose: without it BigQuery adds projectReaders and projectWriters,
  # which would let every Viewer and Editor of the project read the salt.
  access {
    role          = "OWNER"
    special_group = "projectOwners"
  }

  access {
    role          = "OWNER"
    user_by_email = var.secrets_owner
  }

  dynamic "access" {
    for_each = toset(var.secrets_writers)
    content {
      role          = "WRITER"
      user_by_email = access.value
    }
  }

  dynamic "access" {
    for_each = toset(var.secrets_readers)
    content {
      role          = "READER"
      user_by_email = access.value
    }
  }
}
