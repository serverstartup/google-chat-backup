variable "project_id" {
  type        = string
  description = "ID del proyecto GCP donde se habilitan las APIs (p. ej. \"my-project-123\"). Es el PROJECT_ID, no el nombre."
}

variable "services" {
  type        = list(string)
  description = "APIs a habilitar. El script ya no usa People API (los mensajes traen nombre y email); sigue en la lista porque está en el state y quitarla la deshabilitaría en el proyecto."
  default = [
    "chat.googleapis.com",
    "people.googleapis.com",
  ]
}

variable "disable_on_destroy" {
  type        = bool
  description = "Reversibilidad. Si es true (por defecto), 'terraform destroy' DESHABILITA las APIs y revierte el cambio. Ojo: en un proyecto compartido deshabilitar una API afecta a todo el proyecto."
  default     = true
}

# --- Creación opcional del proyecto (avanzado) -------------------------------
# Por defecto se usa un proyecto YA existente (create_project = false).
# Crear el proyecto requiere billing_account y, normalmente, una organización.

variable "create_project" {
  type        = bool
  description = "Si es true, Terraform crea el proyecto. Si es false, usa uno existente."
  default     = false
}

variable "project_name" {
  type        = string
  description = "Nombre visible del proyecto si create_project = true."
  default     = "chatea"
}

variable "billing_account" {
  type        = string
  description = "ID de la cuenta de facturación (XXXXXX-XXXXXX-XXXXXX). Solo si create_project = true."
  default     = ""
}

variable "org_id" {
  type        = string
  description = "ID de la organización. Vacío para proyecto sin organización. Solo si create_project = true."
  default     = ""
}
