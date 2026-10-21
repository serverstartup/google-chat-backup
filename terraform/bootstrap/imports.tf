# Adopts APIs that are already enabled in the project (by hand, with gcloud, or in a state that
# was lost) instead of failing to create them. Off by default, because importing an API that is
# disabled fails: turn it on for one plan with scripts/bootstrap-plan.py --import.
import {
  for_each = var.import_existing_apis ? toset(var.services) : toset([])
  to       = google_project_service.apis[each.value]
  id       = "${var.project_id}/${each.value}"
}
