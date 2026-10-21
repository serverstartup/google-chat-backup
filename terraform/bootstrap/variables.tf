variable "billing_account" {
  type        = string
  description = "Billing account ID (XXXXXX-XXXXXX-XXXXXX). Only if create_project = true."
  default     = ""
}

variable "create_project" {
  type        = bool
  description = "If true, Terraform creates the project. If false, it uses an existing one."
  default     = false
}

variable "disable_on_destroy" {
  type        = bool
  description = "Reversibility. If true (the default), 'terraform destroy' DISABLES the APIs and reverts the change. Careful: in a shared project, disabling an API affects the whole project."
  default     = true
}

variable "import_existing_apis" {
  type        = bool
  description = "If true, the plan imports the APIs in var.services that are already enabled in the project (imports.tf). Use it once, through scripts/bootstrap-plan.py --import."
  default     = false
}

variable "org_id" {
  type        = string
  description = "Organization ID. Empty for a project without an organization. Only if create_project = true."
  default     = ""
}

variable "project_id" {
  type        = string
  description = "ID of the GCP project where the APIs are enabled (e.g. \"my-project-123\"). It is the PROJECT_ID, not the name."
}

variable "project_name" {
  type        = string
  description = "Display name of the project if create_project = true."
  default     = "chatea"
}

variable "services" {
  type        = list(string)
  description = "APIs to enable. The script no longer uses the People API (messages carry name and email); it stays in the list because it is in the state and removing it would disable it in the project."
  default = [
    "chat.googleapis.com",
    "people.googleapis.com",
  ]
}
