# Copyright (c) 2026, abdullahjavaid198@gmail.com and contributors
# For license information, please see license.txt

"""
Add custom fields to Interview DocType for overseas recruitment workflows.
Extends HRMS Interview module without breaking existing functionality.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def check_field_exists(fieldname, doctype="Interview"):
	"""
	Check if a field already exists in Interview (either standard or custom)
	Returns True if field exists, False otherwise
	"""
	try:
		meta = frappe.get_meta(doctype)
		# Check standard fields
		for field in meta.fields:
			if field.fieldname == fieldname:
				return True
		
		# Check custom fields
		if frappe.db.exists("Custom Field", {"dt": doctype, "fieldname": fieldname}):
			return True
		
		return False
	except Exception:
		return False


# Doctypes that may have had an 'application' Link field (Application doctype was removed).
_INTERVIEW_APPLICATION_DOCTYPES = ("Interview", "Interview-application", "Interview Application")


def _remove_application_field_from_doctype(dt):
	"""
	Remove the 'application' field from a doctype (Custom Field or standard DocField).
	Returns True if anything was removed.
	"""
	removed = False
	# 1. Remove Custom Field if it exists
	custom_field = frappe.db.exists("Custom Field", {"dt": dt, "fieldname": "application"})
	if custom_field:
		frappe.delete_doc("Custom Field", custom_field, force=1, ignore_permissions=True)
		removed = True
	# 2. Remove standard DocField if it exists (e.g. on Interview-application child table)
	if frappe.db.exists("DocField", {"parent": dt, "fieldname": "application"}):
		frappe.db.sql(
			"DELETE FROM `tabDocField` WHERE parent = %(parent)s AND fieldname = 'application'",
			{"parent": dt},
		)
		removed = True
	if removed:
		frappe.clear_cache(doctype=dt)
	return removed


@frappe.whitelist()
def remove_application_field_from_interview():
	"""
	Remove the obsolete 'application' field from Interview and Interview-application
	(Custom Field or standard DocField). Application doctype was removed.
	Run this once to fix: 'Field application is referring to non-existing doctype Application' error.
	"""
	removed = []
	for dt in _INTERVIEW_APPLICATION_DOCTYPES:
		if _remove_application_field_from_doctype(dt):
			removed.append(dt)
	if removed:
		frappe.db.commit()
		frappe.msgprint(
			frappe._("Removed 'application' field from: {0}. Application doctype is no longer used.").format(", ".join(removed)),
			indicator="green",
		)
		return {"success": True, "removed": removed}
	frappe.msgprint(frappe._("No 'application' field found on Interview or Interview-application."), indicator="blue")
	return {"success": True, "removed": []}


@frappe.whitelist()
def remove_duplicate_interview_fields():
	"""
	Remove duplicate custom fields that conflict with standard HRMS fields.
	Also removes obsolete 'application' field from Interview and Interview-application (Application doctype removed).
	Run before add_custom_fields_to_interview().
	"""
	duplicate_fields = ["job_opening", "demand", "interview_start", "interview_end", "application"]
	removed_fields = []  # list of (doctype, fieldname) for reporting

	for dt in _INTERVIEW_APPLICATION_DOCTYPES:
		for fieldname in duplicate_fields:
			custom_field = frappe.db.exists("Custom Field", {"dt": dt, "fieldname": fieldname})
			if custom_field:
				try:
					frappe.delete_doc("Custom Field", custom_field, force=1, ignore_permissions=True)
					removed_fields.append(f"{dt}.{fieldname}")
					frappe.clear_cache(doctype=dt)
				except Exception as e:
					frappe.log_error(f"Error removing duplicate field {dt}.{fieldname}: {str(e)}", "Remove Duplicate Interview Fields")

	if removed_fields:
		frappe.db.commit()
		frappe.msgprint(
			frappe._("Removed duplicate/obsolete field(s): {0}").format(", ".join(removed_fields)),
			indicator="orange"
		)
		return {"success": True, "removed": removed_fields}
	else:
		return {"success": True, "removed": [], "message": "No duplicate fields found"}


@frappe.whitelist()
def add_custom_fields_to_interview():
	"""
	Add custom fields to Interview doctype for overseas recruitment.
	Fields are organized into logical sections.
	"""
	# Standard HRMS fields that already exist - DO NOT add these
	existing_standard_fields = [
		"job_applicant",
		"interview_round",
		"interview_date",
		"interview_time",
		"status",
		"interview_details",
		"interview_summary",
		"interview_feedback",
		"result",
		"average_rating",
		"job_opening",  # Standard HRMS field - DO NOT duplicate
		"demand",  # Standard HRMS field - DO NOT duplicate
		"from_time",  # Standard HRMS field - DO NOT duplicate
		"to_time",  # Standard HRMS field - DO NOT duplicate
		"scheduled_on",  # Standard HRMS field - DO NOT duplicate
		"interview_start",  # REMOVED - duplicate, use interview_start_time (Time) instead
		"interview_end",  # REMOVED - duplicate, use interview_end_time (Time) instead
		"column_break_1",
		"column_break_2",
		"section_break_1",
		"section_break_2"
	]
	
	custom_fields = {
		"Interview": [
			# Interview is driven by Job Applicant (Application doctype removed).
			# job_opening and demand are auto-populated from Job Applicant via Python.
			# ============================================
			# SECTION: Interview Classification
			# ============================================
			{
				"fieldname": "column_break_ats",
				"fieldtype": "Column Break",
				"insert_after": "job_applicant"
			},
			{
				"fieldname": "classification_section",
				"fieldtype": "Section Break",
				"label": "Interview Classification",
				"insert_after": "column_break_ats"
			},
			{
				"fieldname": "interview_level",
				"fieldtype": "Select",
				"label": "Interview Level",
				"options": "Internal\nCompany",
				"insert_after": "classification_section"
			},
			{
				"fieldname": "column_break_classification",
				"fieldtype": "Column Break",
				"insert_after": "interview_level"
			},
			{
				"fieldname": "interview_type",
				"fieldtype": "Select",
				"label": "Interview Type",
				"options": "HR\nTechnical\nTrade\nCompany",
				"insert_after": "column_break_classification"
			},
			
			# ============================================
			# SECTION: Feedback (Time-based)
			# ============================================
			{
				"fieldname": "feedback_section",
				"fieldtype": "Section Break",
				"label": "Feedback",
				"insert_after": "interview_type"
			},
			{
				"fieldname": "interview_start_time",
				"fieldtype": "Time",
				"label": "Interview Start Time",
				"insert_after": "feedback_section"
			},
			{
				"fieldname": "column_break_timing",
				"fieldtype": "Column Break",
				"insert_after": "interview_start_time"
			},
			{
				"fieldname": "interview_end_time",
				"fieldtype": "Time",
				"label": "Interview End Time",
				"insert_after": "column_break_timing"
			},
			{
				"fieldname": "total_time",
				"fieldtype": "Data",
				"label": "Total Time",
				"read_only": 1,
				"insert_after": "interview_end_time"
			},
			{
				"fieldname": "interviewer_notes",
				"fieldtype": "Text",
				"label": "Interviewer Notes",
				"insert_after": "total_time"
			},
			
			# ============================================
			# SECTION: Result
			# ============================================
			{
				"fieldname": "result_section",
				"fieldtype": "Section Break",
				"label": "Interview Result",
				"insert_after": "interviewer_notes"
			},
			{
				"fieldname": "interview_result",
				"fieldtype": "Select",
				"label": "Interview Result",
				"options": "Pass\nFail\nHold",
				"insert_after": "result_section"
			},
			# ============================================
			# SECTION: Pipeline Context (from Job Applicant)
			# ============================================
			{
				"fieldname": "pipeline_context_section",
				"fieldtype": "Section Break",
				"label": "Pipeline Context",
				"description": "Job Applicant pipeline and stage (read-only)",
				"insert_after": "interview_result"
			},
			{
				"fieldname": "applicant_pipeline",
				"fieldtype": "Data",
				"label": "Applicant Pipeline",
				"read_only": 1,
				"insert_after": "pipeline_context_section"
			},
			{
				"fieldname": "applicant_current_stage",
				"fieldtype": "Data",
				"label": "Applicant Current Stage",
				"read_only": 1,
				"insert_after": "applicant_pipeline"
			}
		]
	}
	
	try:
		# First, remove any duplicate fields that might have been created
		remove_duplicate_interview_fields()
		
		# Filter out fields that already exist (standard or custom)
		fields_to_add = []
		skipped_fields = []
		
		for field in custom_fields["Interview"]:
			fieldname = field.get("fieldname")
			
			# Skip if it's in the list of existing standard fields
			if fieldname in existing_standard_fields:
				skipped_fields.append(f"{fieldname} (standard field)")
				continue
			
			# Check if field already exists
			if check_field_exists(fieldname, "Interview"):
				skipped_fields.append(f"{fieldname} (already exists)")
				continue
			
			# Add field to list
			fields_to_add.append(field)
		
		# Create custom fields
		if fields_to_add:
			create_custom_fields(
				{"Interview": fields_to_add},
				ignore_validate=True,
				update=True
			)
			
			frappe.db.commit()
			
			message = f"Successfully added {len(fields_to_add)} custom fields to Interview"
			if skipped_fields:
				message += f"\nSkipped {len(skipped_fields)} fields (already exist)"
			
			frappe.msgprint(message, indicator="green")
			
			return {
				"success": True,
				"added": len(fields_to_add),
				"skipped": len(skipped_fields),
				"skipped_fields": skipped_fields
			}
		else:
			frappe.msgprint(
				"No new fields to add. All fields already exist or were skipped.",
				indicator="orange"
			)
			return {
				"success": True,
				"added": 0,
				"skipped": len(skipped_fields),
				"skipped_fields": skipped_fields
			}
		
	except Exception as e:
		error_msg = f"Error adding custom fields to Interview: {str(e)}"
		frappe.log_error(error_msg, "Add Interview Custom Fields Error")
		frappe.msgprint(error_msg, indicator="red")
		return {"success": False, "error": str(e)}
