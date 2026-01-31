# Copyright (c) 2026, abdullahjavaid198@gmail.com and contributors
# For license information, please see license.txt

"""
Install hooks for Recruitment System app.
Uses 2-level package path: recruitment_system.recruitment_system (not three).
"""

import frappe


def after_install():
	"""Create Pipelines and Pipeline Stages, then add custom fields to Job Applicant and Interview."""
	# 1. Create Pipeline and Pipeline Stage records (Interviews, Offer Letter, Visa Process + stages)
	try:
		from recruitment_system.recruitment_system.setup_pipelines import setup_pipelines_and_stages
		result = setup_pipelines_and_stages()
		if result.get("success"):
			frappe.logger().info(
				f"Recruitment System: Pipelines setup - created {result.get('created_pipelines', 0)} pipelines, "
				f"{result.get('created_stages', 0)} stages."
			)
		elif result.get("error"):
			frappe.logger().warning(f"Recruitment System: Pipeline setup skipped - {result.get('error')}")
	except Exception as e:
		frappe.log_error(
			f"Recruitment System after_install: Pipeline setup failed: {str(e)}\n{frappe.get_traceback()}",
			"Recruitment System Install",
		)

	# 2. Add custom fields to Job Applicant (Pipeline & Stages, screening, etc.)
	try:
		from recruitment_system.recruitment_system.doctype.job_applicant_custom_fields.add_custom_fields import add_custom_fields_to_job_applicant
		add_custom_fields_to_job_applicant()
		frappe.logger().info("Recruitment System: Job Applicant custom fields applied.")
	except Exception as e:
		frappe.log_error(
			f"Recruitment System after_install: Job Applicant custom fields failed: {str(e)}\n{frappe.get_traceback()}",
			"Recruitment System Install",
		)

	# 3. Add custom fields to Interview
	try:
		from recruitment_system.recruitment_system.interview.custom_fields import add_custom_fields_to_interview
		add_custom_fields_to_interview()
		frappe.logger().info("Recruitment System: Interview custom fields applied.")
	except Exception as e:
		frappe.log_error(
			f"Recruitment System after_install: Interview custom fields failed: {str(e)}\n{frappe.get_traceback()}",
			"Recruitment System Install",
		)


def after_migrate():
	"""Remove obsolete 'application' field from Interview / Interview-application (fix Missing DocType error)."""
	try:
		from recruitment_system.recruitment_system.interview.custom_fields import remove_application_field_from_interview
		result = remove_application_field_from_interview()
		if result.get("removed"):
			frappe.logger().info(
				f"Recruitment System: Removed 'application' field from {result.get('removed')} (Application doctype removed)."
			)
	except Exception as e:
		frappe.log_error(
			f"Recruitment System after_migrate: remove_application_field failed: {str(e)}\n{frappe.get_traceback()}",
			"Recruitment System Migrate",
		)
