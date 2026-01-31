# Copyright (c) 2026, abdullahjavaid198@gmail.com and contributors
# For license information, please see license.txt

"""
Setup Pipelines and Pipeline Stages for recruitment workflow.
Run once after install or via after_install hook.
"""

import frappe
from frappe import _


# Pipeline definitions: (title, applies_to, [(stage_name, sequence, is_terminal), ...])
PIPELINE_DEFINITIONS = [
	(
		"Interviews",
		"Job Applicant",
		[
			("Screening", 1, False),
			("Internal Interview Held", 2, False),
			("Internally Selected", 3, False),
			("Internal Rejected", 4, True),
			("Company Interview", 5, False),
			("Company Selected", 6, False),
			("Company Rejected", 7, True),
		],
	),
	(
		"Offer Letter",
		"Job Applicant",
		[
			("Offer Letter Waited", 1, False),
			("Offer Letter Received", 2, False),
			("Offer Letter Accepted", 3, False),
		],
	),
	(
		"Visa Process",
		"Visa Process",
		[
			("Medical", 1, False),
			("Takamul", 2, False),
			("Embassy Documentation", 3, False),
			("NAVTTC", 4, False),
			("E-Number Allotted", 5, False),
			("Embassy Visa", 6, False),
			("Protector", 7, False),
			("Ticket", 8, False),
			("Deployment", 9, False),
			("Closed", 10, True),
		],
	),
]


@frappe.whitelist()
def setup_pipelines_and_stages():
	"""
	Create or ensure Pipelines and Pipeline Stages exist.
	Idempotent: safe to run multiple times.
	Returns dict with created/updated counts.
	"""
	if not frappe.db.exists("DocType", "Pipeline"):
		return {"success": False, "error": _("Pipeline doctype not found. Run migrate first.")}
	if not frappe.db.exists("DocType", "Pipeline Stage"):
		return {"success": False, "error": _("Pipeline Stage doctype not found. Run migrate first.")}

	created_pipelines = 0
	created_stages = 0

	for title, applies_to, stages in PIPELINE_DEFINITIONS:
		# Create or get Pipeline (autoname by title)
		if not frappe.db.exists("Pipeline", title):
			doc = frappe.get_doc(
				{
					"doctype": "Pipeline",
					"title": title,
					"is_active": 1,
					"applies_to": applies_to or None,
				}
			)
			doc.insert(ignore_permissions=True)
			created_pipelines += 1

		pipeline_name = title  # autoname is field:title
		# Create Pipeline Stages
		for stage_name, sequence, is_terminal in stages:
			existing = frappe.db.exists(
				"Pipeline Stage",
				{"pipeline": pipeline_name, "stage_name": stage_name},
			)
			if not existing:
				stage_doc = frappe.get_doc(
					{
						"doctype": "Pipeline Stage",
						"pipeline": pipeline_name,
						"stage_name": stage_name,
						"sequence": sequence,
						"is_terminal": 1 if is_terminal else 0,
					}
				)
				stage_doc.insert(ignore_permissions=True)
				created_stages += 1

	frappe.db.commit()
	return {
		"success": True,
		"created_pipelines": created_pipelines,
		"created_stages": created_stages,
		"message": _("Pipelines and stages are ready."),
	}


def get_first_stage_for_pipeline(pipeline_name):
	"""Return the first Pipeline Stage name (by sequence) for a pipeline."""
	if not pipeline_name:
		return None
	stages = frappe.get_all(
		"Pipeline Stage",
		filters={"pipeline": pipeline_name},
		fields=["name", "sequence"],
		order_by="sequence asc",
		limit=1,
	)
	return stages[0]["name"] if stages else None


def get_stage_by_name(pipeline_name, stage_name):
	"""Return Pipeline Stage docname for pipeline + stage_name."""
	if not pipeline_name or not stage_name:
		return None
	return frappe.db.get_value(
		"Pipeline Stage",
		{"pipeline": pipeline_name, "stage_name": stage_name},
		"name",
	)
