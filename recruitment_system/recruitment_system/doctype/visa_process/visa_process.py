# Copyright (c) 2026, abdullahjavaid198@gmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


# Map Pipeline Stage stage_name -> (date_field, status_field, completed_status_values)
VISA_STAGE_FIELDS = {
	"Medical": ("medical_date", "medical_status", ("Done", "Not Required")),
	"Takamul": ("takamul_date", "takamul_status", ("Done", "Not Required")),
	"Embassy Documentation": (
		"embassy_documentation_date",
		"embassy_documentation_status",
		("Done", "Not Required"),
	),
	"NAVTTC": ("navttc_date", "navttc_status", ("Done", "Not Required")),
	"E-Number Allotted": ("e_number_date", "e_number_status", ("Allotted", "Not Required")),
	"Embassy Visa": ("embassy_visa_date", "embassy_visa_status", ("Issued", "Not Required")),
	"Protector": ("protector_date", "protector_status", ("Done", "Not Required")),
	"Ticket": ("ticket_date", "ticket_status", ("Booked", "Received", "Not Required")),
	"Deployment": ("deployment_date", "deployment_status", ("Deployed", "Not Required")),
	"Closed": ("closed_date", None, ()),  # No status field; date only
}


class VisaProcess(Document):
	"""Visa Process document: tracks visa pipeline stages and per-stage dates/status."""

	def validate(self):
		if self.job_applicant and not self.applicant:
			self.set_applicant_from_job_applicant()

	def on_update(self):
		"""After save: advance current_stage to next when current stage is completed; sync stage to Job Applicant."""
		self.advance_stage_if_completed()
		self._sync_stage_to_job_applicant()

	def set_applicant_from_job_applicant(self):
		"""Default applicant from linked Job Applicant."""
		if not self.job_applicant:
			return
		applicant = frappe.db.get_value("Job Applicant", self.job_applicant, "applicant")
		if applicant:
			self.applicant = applicant

	def advance_stage_if_completed(self):
		"""If current stage has date (and status if applicable) set to a completed value, move to next stage."""
		if not self.pipeline or not self.current_stage:
			return
		stage_name = frappe.db.get_value("Pipeline Stage", self.current_stage, "stage_name")
		if not stage_name or stage_name not in VISA_STAGE_FIELDS:
			return
		date_field, status_field, completed_values = VISA_STAGE_FIELDS[stage_name]
		date_value = self.get(date_field)
		if not date_value:
			return
		if status_field:
			status_value = (self.get(status_field) or "").strip()
			if status_value not in completed_values:
				return
		# Current stage is completed; get next stage
		next_stage = self.get_next_stage()
		if next_stage:
			self.db_set("current_stage", next_stage, update_modified=False)
			frappe.db.commit()
			next_name = frappe.db.get_value("Pipeline Stage", next_stage, "stage_name")
			frappe.msgprint(
				_("Stage advanced to '{0}'.").format(next_name or next_stage),
				indicator="green",
			)

	def get_next_stage(self):
		"""Return the next Pipeline Stage name (by sequence) for this pipeline."""
		if not self.pipeline or not self.current_stage:
			return None
		current_seq = frappe.db.get_value("Pipeline Stage", self.current_stage, "sequence")
		if current_seq is None:
			return None
		stages = frappe.get_all(
			"Pipeline Stage",
			filters={"pipeline": self.pipeline},
			fields=["name", "sequence"],
			order_by="sequence asc",
		)
		for s in stages:
			if s["sequence"] > current_seq:
				return s["name"]
		return None

	def _sync_stage_to_job_applicant(self):
		"""
		Keep Job Applicant in sync with Visa Process pipeline and stage.
		When Visa Process pipeline/current_stage is updated (by user or by advance_stage_if_completed),
		set the linked Job Applicant to the same pipeline and current_stage.
		Reads pipeline/current_stage from DB so we sync the persisted state (advance_stage_if_completed
		uses db_set, which does not update in-memory doc).
		Uses db.set_value to avoid triggering Job Applicant on_update (no sync loop).
		"""
		if not self.job_applicant:
			return
		pipeline = frappe.db.get_value("Visa Process", self.name, "pipeline")
		current_stage = frappe.db.get_value("Visa Process", self.name, "current_stage")
		if not pipeline or not current_stage:
			return
		ja_name = self.job_applicant
		frappe.db.set_value("Job Applicant", ja_name, "pipeline", pipeline, update_modified=False)
		frappe.db.set_value("Job Applicant", ja_name, "current_stage", current_stage, update_modified=False)
		frappe.db.commit()
