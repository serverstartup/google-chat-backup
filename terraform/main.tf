# Creación opcional del proyecto. Con create_project = false (por defecto)
# este recurso no se crea y se usa el proyecto indicado en var.project_id.
resource "google_project" "chatea" {
  count           = var.create_project ? 1 : 0
  name            = var.project_name
  project_id      = var.project_id
  billing_account = var.billing_account
  org_id          = var.org_id != "" ? var.org_id : null
}

# Habilita las APIs necesarias. Esto es lo único de toda la configuración
# que Google expone por API y, por tanto, lo único terraformable.
resource "google_project_service" "apis" {
  for_each = toset(var.services)

  project = var.project_id
  service = each.value

  # Reversibilidad: por defecto, 'terraform destroy' deshabilita las APIs.
  # Controlable con var.disable_on_destroy. Ojo en proyectos compartidos.
  disable_on_destroy = var.disable_on_destroy

  # Si el proyecto lo crea este mismo plan, espera a tenerlo.
  depends_on = [google_project.chatea]
}
