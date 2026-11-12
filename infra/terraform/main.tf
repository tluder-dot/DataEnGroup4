# What already exists, described from the real resources (gcloud / the API),
# not from what we think we created. See docs/infra.md for why each one exists.

# The label convention is in docs/costs.md. Four keys on every resource:
# group, environment, layer, lesson. The value of `layer` and `lesson` is set
# per resource below.
locals {
  base_labels = {
    group       = var.group
    environment = "course"
  }
}

resource "google_storage_bucket" "data" {
  name                        = "${var.project_id}-${var.group}"
  location                    = upper(var.region)
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  force_destroy               = false # a non-empty bucket must refuse to be deleted

  labels = merge(local.base_labels, { layer = "bronze", lesson = "l02" })

  soft_delete_policy {
    retention_duration_seconds = 604800 # 7 days, the default we kept
  }

  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
    condition {
      age            = 30
      matches_prefix = ["bronze/"]
    }
  }

  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
    condition {
      age            = 90
      matches_prefix = ["bronze/"]
    }
  }

  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "ARCHIVE"
    }
    condition {
      age            = 365
      matches_prefix = ["bronze/"]
    }
  }
}

resource "google_bigquery_dataset" "bronze" {
  dataset_id  = "${var.group}_bronze_1"
  location    = var.region
  labels      = merge(local.base_labels, { layer = "bronze", lesson = "l02" })
  description = "Group 4 bronze: external tables over gs://data-engineering-i1-g04/bronze/"
}

resource "google_bigquery_dataset" "warehouse" {
  dataset_id  = "${var.group}_warehouse"
  location    = var.region
  labels      = merge(local.base_labels, { layer = "warehouse", lesson = "l04" })
  description = "Group 4: native tables for step 4 (L04)"
}

resource "google_bigquery_dataset" "silver" {
  dataset_id  = "${var.group}_silver"
  location    = var.region
  labels      = merge(local.base_labels, { layer = "silver", lesson = "l05" })
  description = "Group 4 silver, built by dbt from transform/"
}

resource "google_bigquery_dataset" "gold" {
  dataset_id  = "${var.group}_gold"
  location    = var.region
  labels      = merge(local.base_labels, { layer = "gold", lesson = "l05" })
  description = "Group 4 gold, built by dbt from transform/"
}
