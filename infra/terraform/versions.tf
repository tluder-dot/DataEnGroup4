terraform {
  required_version = ">= 1.9"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 8.4"
    }
  }

  # State lives in a versioned bucket made by hand, once (docs/infra.md).
  # The bucket that holds the state cannot be managed by the state it holds.
  backend "gcs" {
    bucket = "data-engineering-i1-g04-tfstate"
    prefix = "platform"
  }
}
