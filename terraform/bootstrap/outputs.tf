output "enabled_services" {
  description = "APIs enabled by this plan."
  value       = [for s in google_project_service.apis : s.service]
}

output "next_steps" {
  description = "Reminder: what is left is manual."
  value       = "APIs enabled. Next, the console steps in docs/how-to/bootstrap.md: Chat app configuration, consent screen and desktop OAuth client. They have no API."
}

output "project_id" {
  description = "Project that was worked on."
  value       = var.project_id
}
