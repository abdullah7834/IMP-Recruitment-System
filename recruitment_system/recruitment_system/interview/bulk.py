# Copyright (c) 2026, abdullahjavaid198@gmail.com and contributors
# For license information, please see license.txt

"""
Bulk Interview Creation Utility
Creates multiple Interview records for a list of Job Applicants (Application doctype removed).
"""

import frappe
from frappe import _
from frappe.utils import getdate, get_time, add_to_date

from recruitment_system.recruitment_system.doctype.job_applicant.job_applicant import (
	get_default_pipeline_and_first_stage,
)


@frappe.whitelist()
def create_bulk_interviews(
	demand=None,
	job_opening=None,
	interview_round=None,
	interview_date=None,
	time_slot=None,
	job_applicants=None,
	start_time=None,
	end_time=None,
	interview_level=None,
	interview_type=None,
	interview_start=None,
	interview_end=None
):
	"""
	Create Interview records in bulk for multiple Job Applicants.

	Parameters:
		demand: Demand name (optional, for filtering)
		job_opening: Job Opening name (optional, for filtering)
		interview_round: Interview Round name (required)
		interview_date: Interview date (required, format: YYYY-MM-DD)
		time_slot: Time slot string (optional, e.g., "09:00:00-10:00:00")
		job_applicants: List of Job Applicant names (required)
		start_time: Start time (optional, format: HH:MM:SS)
		end_time: End time (optional, format: HH:MM:SS)

	Returns:
		Dictionary with success status, created count, and details
	"""
	if not interview_round:
		frappe.throw(_("Interview Round is required"), title=_("Missing Parameter"))
	if not interview_date:
		frappe.throw(_("Interview Date is required"), title=_("Missing Parameter"))
	if not job_applicants:
		frappe.throw(_("Job Applicants list is required"), title=_("Missing Parameter"))

	if not frappe.db.exists("Interview Round", interview_round):
		frappe.throw(
			_("Interview Round '{0}' does not exist").format(interview_round),
			title=_("Invalid Interview Round")
		)

	import json
	if isinstance(job_applicants, str):
		try:
			job_applicants = json.loads(job_applicants)
		except Exception:
			job_applicants = [j.strip() for j in job_applicants.split(",") if j.strip()]

	if not isinstance(job_applicants, list):
		frappe.throw(_("Job Applicants must be a list"), title=_("Invalid Parameter"))

	if time_slot and not start_time and not end_time:
		if "-" in time_slot:
			parts = time_slot.split("-")
			if len(parts) == 2:
				start_time = parts[0].strip()
				end_time = parts[1].strip()

	interview_date_obj = None
	if interview_date:
		try:
			interview_date_obj = getdate(interview_date)
		except Exception:
			frappe.throw(_("Invalid date format. Use YYYY-MM-DD"), title=_("Invalid Date"))

	duration_minutes = None
	if start_time and end_time and not interview_start and not interview_end:
		from datetime import datetime, timedelta
		try:
			start_t = get_time(start_time)
			end_t = get_time(end_time)
			base_date = interview_date_obj if interview_date_obj else getdate()
			start_dt = datetime.combine(base_date, start_t)
			end_dt = datetime.combine(base_date, end_t)
			if end_t < start_t:
				end_dt += timedelta(days=1)
			diff = end_dt - start_dt
			duration_minutes = int(diff.total_seconds() / 60)
		except Exception:
			duration_minutes = 60

	created_interviews = []
	failed_interviews = []

	for job_applicant_name in job_applicants:
		if not job_applicant_name:
			continue
		try:
			if not frappe.db.exists("Job Applicant", job_applicant_name):
				failed_interviews.append({
					"job_applicant": job_applicant_name,
					"error": "Job Applicant does not exist"
				})
				continue

			job_applicant = frappe.get_doc("Job Applicant", job_applicant_name)

			# Start Pipeline and Stage for this applicant if not set (same as on Job Applicant save)
			pipeline = getattr(job_applicant, "pipeline", None)
			current_stage = getattr(job_applicant, "current_stage", None)
			if not pipeline or not current_stage:
				default = get_default_pipeline_and_first_stage("Job Applicant")
				if default:
					frappe.db.set_value("Job Applicant", job_applicant_name, "pipeline", default["pipeline"], update_modified=False)
					frappe.db.set_value("Job Applicant", job_applicant_name, "current_stage", default["current_stage"], update_modified=False)
					# Reload so terminal-stage check and Interview creation use updated values
					job_applicant.reload()
					pipeline = job_applicant.pipeline
					current_stage = job_applicant.current_stage

			existing_interview = frappe.db.exists(
				"Interview",
				{
					"job_applicant": job_applicant_name,
					"interview_round": interview_round
				}
			)
			if existing_interview:
				failed_interviews.append({
					"job_applicant": job_applicant_name,
					"error": _("Interview Round already exists (Interview: {0})").format(existing_interview)
				})
				continue

			# Block if Job Applicant has terminal stage (when pipeline/current_stage is used)
			current_stage = getattr(job_applicant, "current_stage", None)
			if current_stage:
				stage_name = frappe.db.get_value("Pipeline Stage", current_stage, "stage_name")
				if stage_name in ["Internal Rejected", "Company Rejected", "Deployed"]:
					failed_interviews.append({
						"job_applicant": job_applicant_name,
						"error": _("Job Applicant is in '{0}' stage").format(stage_name)
					})
					continue

			# HRMS Interview requires scheduled_on (Date); default to interview date (today if from bulk dialog)
			scheduled_on = interview_date_obj if interview_date_obj else getdate()
			interview_data = {
				"doctype": "Interview",
				"job_applicant": job_applicant_name,
				"interview_round": interview_round,
				"interview_date": interview_date_obj,
				"scheduled_on": scheduled_on,
				"interview_time": start_time if start_time else None
			}
			if start_time:
				interview_data["interview_start_time"] = start_time
				if frappe.get_meta("Interview").has_field("from_time"):
					interview_data["from_time"] = start_time
			if end_time:
				interview_data["interview_end_time"] = end_time
				if frappe.get_meta("Interview").has_field("to_time"):
					interview_data["to_time"] = end_time
			if interview_level:
				interview_data["interview_level"] = interview_level
			if interview_type:
				interview_data["interview_type"] = interview_type

			interview_meta = frappe.get_meta("Interview")
			job_opening_val = getattr(job_applicant, "job_title", None) or getattr(job_applicant, "job_opening", None)
			demand_val = getattr(job_applicant, "linked_demand", None) or getattr(job_applicant, "demand", None)
			if job_opening_val and interview_meta.has_field("job_opening"):
				interview_data["job_opening"] = job_opening_val
			if demand_val and interview_meta.has_field("demand"):
				interview_data["demand"] = demand_val

			interview = frappe.get_doc(interview_data)
			interview.insert(ignore_permissions=True)

			created_interviews.append({
				"interview": interview.name,
				"job_applicant": job_applicant_name
			})
		except Exception as e:
			frappe.log_error(
				f"Error creating Interview for Job Applicant {job_applicant_name}: {str(e)}\n{frappe.get_traceback()}",
				"Bulk Interview Creation Error"
			)
			failed_interviews.append({"job_applicant": job_applicant_name, "error": str(e)})

	frappe.db.commit()

	result = {
		"success": True,
		"created_count": len(created_interviews),
		"failed_count": len(failed_interviews),
		"created_interviews": created_interviews,
		"failed_interviews": failed_interviews
	}
	message = _("Created {0} Interview(s)").format(len(created_interviews))
	if failed_interviews:
		message += _("\nFailed: {0}").format(len(failed_interviews))
	frappe.msgprint(message, indicator="green" if not failed_interviews else "orange")
	return result


@frappe.whitelist()
def get_bulk_interview_selection_context(job_applicant_names):
	"""
	Validate that selected Job Applicants share the same Demand and Demand Position.
	Called from list view before opening the bulk interview dialog.

	Parameters:
		job_applicant_names: List of Job Applicant names (from list view selection)

	Returns:
		dict: { demand, demand_position, job_applicants } if all share same demand and position.
		Raises if selection is empty, or if demand/position differ or are missing.
	"""
	import json
	if isinstance(job_applicant_names, str):
		try:
			job_applicant_names = json.loads(job_applicant_names)
		except Exception:
			job_applicant_names = [n.strip() for n in job_applicant_names.split(",") if n.strip()]
	if not job_applicant_names:
		frappe.throw(_("No Job Applicants selected."), title=_("Selection Required"))
	# Resolve linked_demand and demand_position (custom fields on Job Applicant)
	meta = frappe.get_meta("Job Applicant")
	demand_field = "linked_demand" if meta.has_field("linked_demand") else "demand"
	position_field = "demand_position" if meta.has_field("demand_position") else None
	first_demand = None
	first_position = None
	valid_names = []
	for name in job_applicant_names:
		if not name or not frappe.db.exists("Job Applicant", name):
			continue
		row = frappe.db.get_value(
			"Job Applicant",
			name,
			[demand_field, position_field] if position_field else [demand_field],
			as_dict=True,
		)
		if not row:
			continue
		demand = row.get(demand_field)
		position = row.get(position_field) if position_field else None
		if not demand:
			frappe.throw(
				_("Job Applicant '{0}' has no Demand linked. All selected must have the same Demand and Demand Position.").format(name),
				title=_("Invalid Selection"),
			)
		if first_demand is None:
			first_demand = demand
			first_position = position
			valid_names.append(name)
		else:
			if demand != first_demand or (position_field and position != first_position):
				frappe.throw(
					_("All selected Job Applicants must have the same Demand and Demand Position. '{0}' differs.").format(name),
					title=_("Same Demand Required"),
				)
			valid_names.append(name)
	if not valid_names:
		frappe.throw(_("No valid Job Applicants in selection."), title=_("Selection Required"))
	return {
		"demand": first_demand,
		"demand_position": first_position or "",
		"job_applicants": valid_names,
		"count": len(valid_names),
	}


@frappe.whitelist()
def get_job_applicants_for_bulk_interview(demand=None, job_opening=None):
	"""
	Get list of Job Applicants for bulk interview creation.

	Parameters:
		demand: Demand name (optional filter)
		job_opening: Job Opening name (optional filter) - maps to Job Applicant job_title

	Returns:
		List of Job Applicants with details
	"""
	filters = {}
	if demand:
		filters["linked_demand"] = demand
	if job_opening:
		filters["job_title"] = job_opening

	job_applicants = frappe.get_all(
		"Job Applicant",
		filters=filters,
		fields=["name", "applicant", "job_title", "linked_demand", "applicant_name", "email_id"],
		order_by="name asc"
	)
	return job_applicants
