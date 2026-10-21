terraform {
  required_version = ">= 1.7" # for_each in import blocks

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}
