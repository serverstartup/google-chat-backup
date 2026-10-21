output "project_id" {
  description = "Project that was worked on."
  value       = var.project_id
}

output "enabled_services" {
  description = "APIs enabled by this plan."
  value       = [for s in google_project_service.apis : s.service]
}

output "next_steps" {
  description = "Reminder: what is left is manual."
  value       = "APIs enabled. Next, the steps in docs/MANUAL_STEPS.md: consent screen, desktop OAuth client and Chat app configuration. They have no API."
}
