# Copyright (c) 2026, abdullahjavaid198@gmail.com and contributors
# For license information, please see license.txt

"""
Custom logic for Interview DocType
Extends HRMS Interview module for overseas recruitment workflows.
Interview is driven by Job Applicant (Application doctype removed).
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_time, get_datetime, getdate
from datetime import datetime, timedelta


class Interview(Document):
	"""
	Custom Interview class extending HRMS Interview
	Adds overseas recruitment workflow logic. Uses Job Applicant as the hub.
	"""

	def validate(self):
		"""
		Main validation method called before saving Interview
		"""
		# Job Applicant is required (HRMS standard)
		if not self.job_applicant:
			frappe.throw(
				_("Job Applicant is required."),
				title=_("Missing Job Applicant")
			)

		# Auto-populate job_opening and demand from Job Applicant
		self.auto_populate_from_job_applicant()

		# Calculate total time if start and end times are provided
		self.calculate_total_time()

		# Validate interview can be created/updated based on Job Applicant
		self.validate_interview_allowed()

		# Check for duplicate Interview Round per Job Applicant
		self.check_duplicate_interview_round()

	def after_insert(self):
		"""
		Called after Interview is first created.
		When an Interview is created for a Job Applicant in Screening, advance stage to next (e.g. Internal Interview Held).
		"""
		self.advance_job_applicant_stage_on_interview_created()

	def on_update(self):
		"""
		Called after Interview is saved.
		Syncs Job Applicant stage only when Interview status is "cleared" (Cleared or Rejected),
		so pipeline/stage change happens when the user marks the interview as cleared, not when result is typed.
		"""
		if (
			self.job_applicant
			and getattr(self, "status", None) in ("Cleared", "Rejected")
			and self.has_value_changed("status")
		):
			self.sync_to_job_applicant()

	def _is_client_or_company_interview(self):
		"""True if this Interview is Client/Company level (for stage advance to Company Interview)."""
		if hasattr(self, "interview_level") and self.interview_level:
			return self.interview_level in ("Client", "Company")
		if self.interview_round:
			try:
				round_doc = frappe.get_doc("Interview Round", self.interview_round)
				rn = (round_doc.round_name or "").lower()
				return "client" in rn or "company" in rn
			except frappe.DoesNotExistError:
				pass
		return False

	def advance_job_applicant_stage_on_interview_created(self):
		"""
		When an Interview is created for a Job Applicant:
		- In Screening → advance to next stage (e.g. Internal Interview Held).
		- In Internally Selected + Client/Company Interview → advance to Company Interview.
		All values from DB.
		"""
		if not self.job_applicant:
			return
		try:
			job_applicant = frappe.get_doc("Job Applicant", self.job_applicant)
		except frappe.DoesNotExistError:
			return

		pipeline = getattr(job_applicant, "pipeline", None)
		current_stage = getattr(job_applicant, "current_stage", None)
		if not pipeline or not current_stage:
			return

		from recruitment_system.recruitment_system.doctype.job_applicant.job_applicant import (
			get_next_stage_after,
			get_stage_name_for_docname,
			get_stage_by_pipeline_and_name,
		)

		current_stage_name = get_stage_name_for_docname(current_stage)
		next_stage = None
		message_key = None

		if current_stage_name == "Screening":
			next_stage = get_next_stage_after(current_stage)
			message_key = "Screening"
		elif current_stage_name == "Internally Selected" and self._is_client_or_company_interview():
			next_stage = get_stage_by_pipeline_and_name(pipeline, "Company Interview")
			message_key = "Internally Selected"

		if not next_stage or not message_key:
			return

		job_applicant.db_set("current_stage", next_stage, update_modified=False)
		frappe.db.commit()
		next_stage_name = get_stage_name_for_docname(next_stage)
		frappe.msgprint(
			_("Job Applicant stage advanced from {0} to '{1}' (Interview created).").format(
				message_key, next_stage_name or next_stage
			),
			indicator="blue",
		)

	def auto_populate_from_job_applicant(self):
		"""
		Auto-populate job_opening and demand from Job Applicant
		"""
		if not self.job_applicant:
			return

		try:
			job_applicant = frappe.get_doc("Job Applicant", self.job_applicant)
			meta = frappe.get_meta("Interview")

			if meta.has_field("job_opening"):
				# Job Opening is job_title in HRMS Job Applicant
				job_opening = getattr(job_applicant, "job_title", None) or getattr(
					job_applicant, "job_opening", None
				)
				if job_opening and not self.job_opening:
					self.job_opening = job_opening

			if meta.has_field("demand"):
				demand = getattr(job_applicant, "linked_demand", None) or getattr(
					job_applicant, "demand", None
				)
				if demand and not self.demand:
					self.demand = demand

			if hasattr(self, "interview_start_time") and self.interview_start_time:
				if not getattr(self, "interview_time", None):
					self.interview_time = get_time(self.interview_start_time)
		except frappe.DoesNotExistError:
			pass
		except Exception as e:
			frappe.log_error(
				f"Error auto-populating from Job Applicant: {str(e)}",
				"Interview Auto-populate Error",
			)

	def calculate_total_time(self):
		"""
		Calculate total interview time from interview_start_time and interview_end_time
		"""
		if not hasattr(self, "interview_start_time") or not self.interview_start_time:
			self.total_time = None
			return
		if not hasattr(self, "interview_end_time") or not self.interview_end_time:
			self.total_time = None
			return

		try:
			start_time = get_time(self.interview_start_time)
			end_time = get_time(self.interview_end_time)
			base_date = (
				self.interview_date
				if hasattr(self, "interview_date") and self.interview_date
				else getdate()
			)
			start_dt = datetime.combine(base_date, start_time)
			end_dt = datetime.combine(base_date, end_time)
			if end_time < start_time:
				end_dt += timedelta(days=1)
			diff = end_dt - start_dt
			diff_seconds = diff.total_seconds()
			if diff_seconds <= 0:
				self.total_time = None
				return
			total_minutes = int(diff_seconds / 60)
			hours = total_minutes // 60
			minutes = total_minutes % 60
			if hours > 0 and minutes > 0:
				self.total_time = f"{hours} hour{'s' if hours > 1 else ''} {minutes} minute{'s' if minutes > 1 else ''}"
			elif hours > 0:
				self.total_time = f"{hours} hour{'s' if hours > 1 else ''}"
			else:
				self.total_time = f"{minutes} minute{'s' if minutes > 1 else ''}"
		except Exception as e:
			frappe.log_error(
				f"Error calculating total time: {str(e)}\n{frappe.get_traceback()}",
				"Interview Total Time Calculation Error",
			)
			self.total_time = None

	def validate_interview_allowed(self):
		"""
		Validate that interview can be created/updated based on Job Applicant.
		Uses pipeline/current_stage on Job Applicant when available.
		"""
		if not self.job_applicant:
			return

		try:
			job_applicant = frappe.get_doc("Job Applicant", self.job_applicant)
		except frappe.DoesNotExistError:
			return

		# If Job Applicant has current_stage (pipeline), block terminal stages
		current_stage = getattr(job_applicant, "current_stage", None)
		if current_stage:
			stage_doc = frappe.db.get_value(
				"Pipeline Stage", current_stage, ["stage_name"], as_dict=True
			)
			if stage_doc and stage_doc.get("stage_name"):
				blocked_stages = ["Internal Rejected", "Company Rejected", "Deployed"]
				if stage_doc["stage_name"] in blocked_stages:
					frappe.throw(
						_("Cannot create/update Interview. Job Applicant is in '{0}' stage.").format(
							stage_doc["stage_name"]
						),
						title=_("Interview Not Allowed"),
					)

		# Validate Interview Round sequence (Company only after Internal Pass)
		if self.interview_round:
			self.validate_interview_round_sequence(job_applicant)

	def validate_interview_round_sequence(self, job_applicant):
		"""
		Company Interview can only happen after Internal Pass for this Job Applicant.
		"""
		is_Company_interview = False
		if hasattr(self, "interview_level") and self.interview_level:
			is_Company_interview = self.interview_level == "Company"
		elif self.interview_round:
			try:
				interview_round = frappe.get_doc("Interview Round", self.interview_round)
				round_name = (interview_round.round_name or "").lower()
				is_Company_interview = "Company" in round_name or "company" in round_name
			except frappe.DoesNotExistError:
				pass

		if not is_Company_interview:
			return

		# Check for Pass result from Internal interviews for this Job Applicant
		internal_passed = frappe.db.exists(
			"Interview",
			{
				"job_applicant": self.job_applicant,
				"interview_result": "Pass",
				"name": ["!=", self.name],
			},
		)
		if internal_passed:
			return

		# Also allow if Job Applicant current_stage suggests internal selected
		current_stage = getattr(job_applicant, "current_stage", None)
		if current_stage:
			stage_name = frappe.db.get_value("Pipeline Stage", current_stage, "stage_name")
			if stage_name in ["Internally Selected", "Batched"]:
				return

		frappe.throw(
			_("Company Interview can only be scheduled after Internal Interview is Passed."),
			title=_("Invalid Interview Sequence"),
		)

	def check_duplicate_interview_round(self):
		"""
		Warn if another Interview with same Round exists for this Job Applicant.
		"""
		if not self.job_applicant or not self.interview_round:
			return

		existing = frappe.db.exists(
			"Interview",
			{
				"job_applicant": self.job_applicant,
				"interview_round": self.interview_round,
				"name": ["!=", self.name],
			},
		)
		if existing:
			frappe.msgprint(
				_("Warning: Another Interview with Round '{0}' already exists for this Job Applicant: {1}").format(
					self.interview_round, existing
				),
				indicator="orange",
				title=_("Duplicate Interview Round"),
			)

	def sync_to_job_applicant(self):
		"""
		Sync Job Applicant stage when Interview status is Cleared or Rejected.
		Uses status (Cleared=Pass, Rejected=Fail) so pipeline/stage updates only when status is "cleared".
		"""
		status = getattr(self, "status", None)
		if not self.job_applicant or status not in ("Cleared", "Rejected"):
			return
		# Derive result from status: Cleared → Pass, Rejected → Fail
		effective_result = "Pass" if status == "Cleared" else "Fail"

		try:
			job_applicant = frappe.get_doc("Job Applicant", self.job_applicant)
		except frappe.DoesNotExistError:
			return

		# Only sync if Job Applicant has pipeline/current_stage
		pipeline = getattr(job_applicant, "pipeline", None)
		current_stage = getattr(job_applicant, "current_stage", None)
		if not pipeline or not current_stage:
			return

		is_internal = False
		is_client_or_company = False
		if hasattr(self, "interview_level") and self.interview_level:
			is_internal = self.interview_level == "Internal"
			is_client_or_company = self.interview_level in ("Client", "Company")
		elif self.interview_round:
			try:
				interview_round = frappe.get_doc("Interview Round", self.interview_round)
				round_name_lower = (interview_round.round_name or "").lower()
				is_internal = (
					"internal" in round_name_lower
					or "hr" in round_name_lower
					or "technical" in round_name_lower
				)
				is_client_or_company = "client" in round_name_lower or "company" in round_name_lower
			except frappe.DoesNotExistError:
				pass

		# Resolve next stage from Pipeline Stage (same pipeline, next sequence)
		current_seq = frappe.db.get_value("Pipeline Stage", current_stage, "sequence")
		if current_seq is None:
			return

		stages = frappe.get_all(
			"Pipeline Stage",
			filters={"pipeline": pipeline},
			fields=["name", "stage_name", "sequence"],
			order_by="sequence",
		)
		stage_by_seq = {s["sequence"]: s for s in stages}

		def get_next_stage_name():
			for seq in sorted(stage_by_seq.keys()):
				if seq > current_seq:
					return stage_by_seq[seq].get("name"), stage_by_seq[seq].get("stage_name")
			return None, None

		def get_stage_by_name(name):
			for s in stages:
				if s.get("stage_name") == name:
					return s.get("name")
			return None

		stage_updated = False
		new_stage_id = None

		if is_internal:
			if effective_result == "Pass":
				new_stage_id = get_stage_by_name("Internally Selected")
				if not new_stage_id:
					next_id, _ignored = get_next_stage_name()
					new_stage_id = next_id
				if new_stage_id and new_stage_id != current_stage:
					job_applicant.current_stage = new_stage_id
					stage_updated = True
			elif effective_result == "Fail":
				new_stage_id = get_stage_by_name("Internal Rejected")
				if new_stage_id:
					job_applicant.current_stage = new_stage_id
					stage_updated = True

		elif is_client_or_company:
			if effective_result == "Pass":
				new_stage_id = get_stage_by_name("Company Selected")
				if not new_stage_id:
					next_id, _ignored = get_next_stage_name()
					new_stage_id = next_id
				if new_stage_id and new_stage_id != current_stage:
					job_applicant.current_stage = new_stage_id
					stage_updated = True
					# Company Selected → set selection date (if field exists) and move to Offer Letter pipeline
					from frappe.utils import today
					from recruitment_system.recruitment_system.doctype.job_applicant.job_applicant import get_stage_by_pipeline_and_name
					ja_meta = frappe.get_meta("Job Applicant")
					date_field = "Company_selection_date" if ja_meta.has_field("Company_selection_date") else ("client_selection_date" if ja_meta.has_field("client_selection_date") else None)
					if date_field:
						job_applicant.db_set(date_field, today(), update_modified=False)
					offer_waited = get_stage_by_pipeline_and_name("Offer Letter", "Offer Letter Waited")
					if offer_waited and frappe.db.exists("Pipeline", "Offer Letter"):
						job_applicant.db_set("pipeline", "Offer Letter", update_modified=False)
						job_applicant.db_set("current_stage", offer_waited, update_modified=False)
						stage_updated = True
			elif effective_result == "Fail":
				new_stage_id = get_stage_by_name("Company Rejected")
				if new_stage_id:
					job_applicant.current_stage = new_stage_id
					stage_updated = True

		if stage_updated:
			job_applicant.save(ignore_permissions=True)
			frappe.db.commit()
			new_name = frappe.db.get_value("Pipeline Stage", job_applicant.current_stage, "stage_name")
			frappe.msgprint(
				_("Job Applicant stage updated to '{0}' (Interview status: {1}).").format(
					new_name or job_applicant.current_stage, status
				),
				indicator="green",
			)
