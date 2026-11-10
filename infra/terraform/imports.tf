# Adopt what was made by hand in L02 to L05. After the first apply these blocks
# do nothing; they stay as the record of what was imported and from which id.

import {
  to = google_storage_bucket.data
  id = "${var.project_id}/${var.project_id}-${var.group}"
}

import {
  to = google_bigquery_dataset.bronze
  id = "projects/${var.project_id}/datasets/${var.group}_bronze_1"
}

import {
  to = google_bigquery_dataset.warehouse
  id = "projects/${var.project_id}/datasets/${var.group}_warehouse"
}

import {
  to = google_bigquery_dataset.silver
  id = "projects/${var.project_id}/datasets/${var.group}_silver"
}

import {
  to = google_bigquery_dataset.gold
  id = "projects/${var.project_id}/datasets/${var.group}_gold"
}
