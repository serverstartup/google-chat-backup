# Optional project creation. With create_project = false (the default)
# this resource is not created and the project given in var.project_id is used.
resource "google_project" "chatea" {
  count           = var.create_project ? 1 : 0
  name            = var.project_name
  project_id      = var.project_id
  billing_account = var.billing_account
  org_id          = var.org_id != "" ? var.org_id : null
}

# Enables the required APIs. This is the only part of the whole setup
# that Google exposes through an API and, therefore, the only part Terraform can manage.
resource "google_project_service" "apis" {
  for_each = toset(var.services)

  project = var.project_id
  service = each.value

  # Reversibility: by default, 'terraform destroy' disables the APIs.
  # Controlled by var.disable_on_destroy. Careful with shared projects.
  disable_on_destroy = var.disable_on_destroy

  # If this same plan creates the project, wait until it exists.
  depends_on = [google_project.chatea]
}
