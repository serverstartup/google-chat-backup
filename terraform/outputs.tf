output "project_id" {
  description = "Proyecto sobre el que se ha trabajado."
  value       = var.project_id
}

output "enabled_services" {
  description = "APIs habilitadas por este plan."
  value       = [for s in google_project_service.apis : s.service]
}

output "next_steps" {
  description = "Recordatorio: lo que falta es manual."
  value       = "APIs habilitadas. Ahora los pasos de docs/MANUAL_STEPS.md: pantalla de consentimiento, cliente OAuth de escritorio y config de la Chat app. No tienen API."
}
