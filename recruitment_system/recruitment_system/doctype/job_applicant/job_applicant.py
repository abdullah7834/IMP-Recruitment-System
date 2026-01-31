# Copyright (c) 2026, abdullahjavaid198@gmail.com and contributors
# For license information, please see license.txt

"""
Custom validation and methods for Job Applicant DocType
Extends standard Frappe HR Job Applicant. Pipeline/stages managed on Job Applicant (Application doctype removed).
"""

import frappe  # pyright: ignore[reportMissingImports]
from frappe import _  # pyright: ignore[reportMissingImports]
from frappe.model.document import Document  # pyright: ignore[reportMissingImports]
from frappe.utils import getdate, add_months, today, nowdate, cstr  # pyright: ignore[reportMissingImports]
from datetime import datetime


def get_first_stage_for_pipeline_name(pipeline_name):
	"""
	Return the first Pipeline Stage name (by sequence) for a pipeline. From DB only.
	Pipeline Stage autoname can be autoincrement, so name is returned as string for Link field.
	"""
	if not pipeline_name:
		return None
	stages = frappe.get_all(
		"Pipeline Stage",
		filters={"pipeline": pipeline_name},
		fields=["name"],
		order_by="sequence asc",
		limit=1,
	)
	return cstr(stages[0]["name"]) if stages else None
def get_next_stage_after(current_stage_docname):
	"""
	Return the next Pipeline Stage (by sequence) for the same pipeline as current_stage. From DB only.
	Used when creating an Interview to advance Job Applicant from Screening to Internal Interview Held.
	Returns stage docname as string or None if no next stage.
	"""
	if not current_stage_docname:
		return None
	row = frappe.db.get_value(
		"Pipeline Stage",
		current_stage_docname,
		["pipeline", "sequence"],
		as_dict=True,
	)
	if not row or row.sequence is None:
		return None
	stages = frappe.get_all(
		"Pipeline Stage",
		filters={"pipeline": row.pipeline, "sequence": (">", row.sequence)},
		fields=["name", "sequence"],
		order_by="sequence asc",
		limit=1,
	)
	return cstr(stages[0]["name"]) if stages else None


def get_stage_name_for_docname(stage_docname):
	"""Return stage_name (e.g. 'Screening') for a Pipeline Stage docname. From DB."""
	if not stage_docname:
		return None
	return frappe.db.get_value("Pipeline Stage", stage_docname, "stage_name")


def get_stage_by_pipeline_and_name(pipeline_name, stage_name):
	"""Return Pipeline Stage docname for a pipeline + stage_name. From DB. For use in Interview sync."""
	if not pipeline_name or not stage_name:
		return None
	name = frappe.db.get_value(
		"Pipeline Stage",
		{"pipeline": pipeline_name, "stage_name": stage_name},
		"name",
	)
	return cstr(name) if name else None


def get_default_pipeline_and_first_stage(applies_to):
	"""
	Get the default pipeline and its first stage from the database for a given applies_to (e.g. "Job Applicant", "Visa Process").
	Returns {"pipeline": name, "current_stage": first_stage_name} or None if not found.
	All values from DB; current_stage is string for Link field.
	"""
	if not applies_to:
		return None
	pipelines = frappe.get_all(
		"Pipeline",
		filters={"applies_to": applies_to, "is_active": 1},
		fields=["name"],
		order_by="name asc",
		limit=1,
	)
	if not pipelines:
		return None
	pipeline_name = pipelines[0].get("name")
	first_stage = get_first_stage_for_pipeline_name(pipeline_name)
	if not first_stage:
		return None
	# Ensure string for Link field (Pipeline Stage name can be autoincrement)
	return {"pipeline": pipeline_name, "current_stage": cstr(first_stage)}


class JobApplicant(Document):
	"""
	Custom Job Applicant class with validation. Pipeline and stages are managed on Job Applicant.
	"""

	def validate(self):
		"""
		Main validation method called before saving Job Applicant.
		Auto-sets Pipeline and first stage when empty (no ready_for_pipeline check required).
		Optionally validates ready_for_pipeline when user checks it.
		"""
		# Always set Pipeline and first stage when missing (removes need to check "Ready for Application Pipeline")
		self._set_initial_pipeline_and_stage_if_empty()
		if self.has_value_changed("ready_for_pipeline") and self.ready_for_pipeline:
			self.validate_ready_for_pipeline()
		# Set offer/selection dates when stage changes (for Offer Letter pipeline)
		self._set_dates_from_stage()

	def on_update(self):
		"""After save: set pipeline and first stage when still missing (e.g. API or list update)."""
		self._set_initial_pipeline_if_empty_after_save()

	def _set_initial_pipeline_and_stage_if_empty(self):
		"""
		When Pipeline or Current Stage is empty: set to default for Job Applicant
		(from DB: first active pipeline where applies_to = "Job Applicant" and its first stage).
		Runs in validate() so values are persisted with the document. No ready_for_pipeline check.
		"""
		if not getattr(self, "pipeline", None) or not getattr(self, "current_stage", None):
			default = get_default_pipeline_and_first_stage("Job Applicant")
			if default:
				self.pipeline = default["pipeline"]
				self.current_stage = default["current_stage"]

	def _set_initial_pipeline_if_empty_after_save(self):
		"""
		Fallback: set pipeline and first stage after save when they are still missing
		(e.g. API or list update). No ready_for_pipeline check.
		"""
		if getattr(self, "pipeline", None) and getattr(self, "current_stage", None):
			return
		default = get_default_pipeline_and_first_stage("Job Applicant")
		if not default:
			return
		self.db_set("pipeline", default["pipeline"], update_modified=False)
		self.db_set("current_stage", default["current_stage"], update_modified=False)
		frappe.db.commit()

	def _set_dates_from_stage(self):
		"""
		Set stage-based dates when Pipeline is Offer Letter (or Company Selected).
		Offer Letter Received → set offer_letter_received_date.
		Offer Letter Accepted → set offer_letter_accepted_date.
		Company Selected → set Company_selection_date (if field exists).
		"""
		if not self.get("current_stage"):
			return
		stage_name = frappe.db.get_value("Pipeline Stage", self.current_stage, "stage_name")
		if not stage_name:
			return
		today_date = today()
		meta = frappe.get_meta("Job Applicant")

		if stage_name == "Company Selected":
			for fieldname in ("Company_selection_date", "client_selection_date"):
				if meta.has_field(fieldname) and not self.get(fieldname):
					self.set(fieldname, today_date)
					break
		elif stage_name == "Offer Letter Received":
			if meta.has_field("offer_letter_received_date") and not self.get("offer_letter_received_date"):
				self.offer_letter_received_date = today_date
		elif stage_name == "Offer Letter Accepted":
			if meta.has_field("offer_letter_accepted_date") and not self.get("offer_letter_accepted_date"):
				self.offer_letter_accepted_date = today_date
			# Also set offer_letter_received_date if we're in Accepted but received date not set (e.g. stage moved directly)
			if meta.has_field("offer_letter_received_date") and not self.get("offer_letter_received_date"):
				self.offer_letter_received_date = today_date

	@frappe.whitelist()
	def start_visa_process(self):
		"""
		Create Visa Process document and link to this Job Applicant.
		Allowed only when current stage is Offer Letter Accepted.
		Returns dict with success and visa_process name.
		"""
		if not self.applicant:
			frappe.throw(_("Applicant is required."), title=_("Validation"))
		current_stage = self.get("current_stage")
		if not current_stage:
			frappe.throw(
				_("Pipeline stage is not set. Please set Pipeline and Current Stage first."),
				title=_("Validation"),
			)
		stage_name = frappe.db.get_value("Pipeline Stage", current_stage, "stage_name")
		if stage_name != "Offer Letter Accepted":
			frappe.throw(
				_("Start Visa Process is only allowed when Current Stage is 'Offer Letter Accepted'."),
				title=_("Invalid Stage"),
			)
		if self.get("visa_process"):
			frappe.throw(
				_("Visa Process already created: {0}").format(self.visa_process),
				title=_("Already Started"),
			)
		visa_default = get_default_pipeline_and_first_stage("Visa Process")
		if not visa_default:
			frappe.throw(
				_("Visa Process pipeline not found. Please run 'Setup Pipelines and Stages' first."),
				title=_("Setup Required"),
			)

		visa_process = frappe.get_doc(
			{
				"doctype": "Visa Process",
				"job_applicant": self.name,
				"applicant": self.applicant,
				"pipeline": visa_default["pipeline"],
				"current_stage": visa_default["current_stage"],
				"started_on": today(),
			}
		)
		visa_process.insert(ignore_permissions=True)
		self.db_set("visa_process", visa_process.name, update_modified=False)
		frappe.db.commit()
		return {
			"success": True,
			"visa_process": visa_process.name,
			"message": _("Visa Process {0} created.").format(visa_process.name),
		}

	def validate_ready_for_pipeline(self):
		"""
		Comprehensive validation before allowing ready_for_pipeline = TRUE
		Runs all mandatory system checks and throws clear error messages
		"""
		errors = []
		
		# 1. Applicant Checks
		applicant_errors = self._validate_applicant_checks()
		errors.extend(applicant_errors)
		
		# 2. Passport Checks
		passport_errors = self._validate_passport_checks()
		errors.extend(passport_errors)
		
		# 3. Job & Demand Checks
		job_errors = self._validate_job_demand_checks()
		errors.extend(job_errors)
		
		# 4. Document Checks
		document_errors = self._validate_document_checks()
		errors.extend(document_errors)
		
		# If any errors found, throw with clear message
		if errors:
			error_message = _("Cannot mark as 'Ready for Pipeline'. Please fix the following issues:\n\n")
			error_message += "\n".join([f"• {error}" for error in errors])
			frappe.throw(error_message, title=_("Validation Failed"))
	
	def _validate_applicant_checks(self):
		"""
		Validate Applicant-related checks
		Returns: List of error messages (empty if all pass)
		"""
		errors = []
		
		# Check if applicant is linked
		if not self.applicant:
			errors.append(_("Applicant (Master) must be linked"))
			return errors  # Return early if no applicant
		
		# Get Applicant document
		try:
			applicant_doc = frappe.get_doc("Applicant", self.applicant)
		except frappe.DoesNotExistError:
			errors.append(_("Linked Applicant '{0}' does not exist").format(self.applicant))
			return errors
		
		# Check CNIC exists and is unique
		if not applicant_doc.cnic:
			errors.append(_("Applicant CNIC is missing"))
		else:
			# Check uniqueness (should already be enforced, but double-check)
			duplicate = frappe.db.exists(
				"Applicant",
				{
					"cnic": applicant_doc.cnic,
					"name": ["!=", applicant_doc.name]
				}
			)
			if duplicate:
				errors.append(_("Applicant CNIC '{0}' is not unique").format(applicant_doc.cnic))
		
		# Deployed check can be added later via Visa Process or Job Applicant pipeline stage
		return errors
	
	def _validate_passport_checks(self):
		"""
		Validate Passport-related checks from linked Applicant
		Note: Passport expiry < 6 months is a WARNING, not an error (does not block)
		Returns: List of error messages (empty if all pass)
		"""
		errors = []
		
		if not self.applicant:
			return errors
		
		try:
			applicant_doc = frappe.get_doc("Applicant", self.applicant)
		except frappe.DoesNotExistError:
			return errors
		
		# Check passport number exists
		if not applicant_doc.passport_number:
			errors.append(_("Applicant Passport Number is missing"))
			return errors  # Return early if no passport number
		
		# Check passport expiry date exists
		if not applicant_doc.passport_expiry_date:
			errors.append(_("Applicant Passport Expiry Date is missing"))
			return errors
		
		# Note: Passport expiry < 6 months is now a WARNING, not an error
		# The warning will be shown via get_passport_expiry_warning() method
		# This allows the user to proceed but with awareness
		
		return errors
	
	def _validate_job_demand_checks(self):
		"""
		Validate Job Opening and Demand-related checks
		Returns: List of error messages (empty if all pass)
		"""
		errors = []
		
		# Check Job Opening is linked
		if not self.job_title:
			errors.append(_("Job Opening must be linked"))
			return errors  # Return early if no job opening
		
		try:
			job_opening = frappe.get_doc("Job Opening", self.job_title)
		except frappe.DoesNotExistError:
			errors.append(_("Linked Job Opening '{0}' does not exist").format(self.job_title))
			return errors
		
		# Check Job Opening status = Open
		if job_opening.status != "Open":
			errors.append(
				_("Job Opening '{0}' status is '{1}'. It must be 'Open' to proceed").format(
					self.job_title,
					job_opening.status or _("Not Set")
				)
			)
		
		# Check Job Opening has linked_demand
		if not job_opening.linked_demand:
			errors.append(_("Job Opening '{0}' must have a Linked Demand").format(self.job_title))
		
		# Check Job Opening has demand_position
		if not job_opening.demand_position:
			errors.append(_("Job Opening '{0}' must have a Demand Position").format(self.job_title))
		
		return errors
	
	def _validate_document_checks(self):
		"""
		Validate minimum required documents are uploaded
		Returns: List of error messages (empty if all pass)
		"""
		errors = []
		
		if not self.applicant:
			return errors
		
		try:
			applicant_doc = frappe.get_doc("Applicant", self.applicant)
		except frappe.DoesNotExistError:
			return errors
		
		# Required documents: Passport, CNIC, CV
		required_docs = ["Passport", "CNIC", "CV"]
		missing_docs = []
		
		# Get all uploaded documents from applicant_document child table
		if hasattr(applicant_doc, 'applicant_document') and applicant_doc.applicant_document:
			uploaded_doc_types = []
			for doc_row in applicant_doc.applicant_document:
				if doc_row.document_type and doc_row.file:
					uploaded_doc_types.append(doc_row.document_type)
			
			# Check for missing required documents
			for req_doc in required_docs:
				if req_doc not in uploaded_doc_types:
					missing_docs.append(req_doc)
		else:
			# No documents uploaded at all
			missing_docs = required_docs
		
		if missing_docs:
			errors.append(
				_("Missing required documents: {0}").format(", ".join(missing_docs))
			)
		
		return errors
	
	@frappe.whitelist()
	def get_passport_expiry_warning(self):
		"""
		Check if passport expires within 6 months and return warning message
		This is informational only - does not block the user
		
		Returns: Dictionary with has_warning (bool) and message (str) if warning exists
		"""
		if not self.applicant:
			return {"has_warning": False}
		
		try:
			applicant_doc = frappe.get_doc("Applicant", self.applicant)
		except frappe.DoesNotExistError:
			return {"has_warning": False}
		
		# Check if passport expiry date exists
		if not applicant_doc.passport_expiry_date:
			return {"has_warning": False}
		
		# Calculate 6 months from today
		today_date = getdate(today())
		six_months_from_today = add_months(today_date, 6)
		passport_expiry = getdate(applicant_doc.passport_expiry_date)
		
		# Check if passport expires within 6 months
		if passport_expiry < six_months_from_today:
			# Calculate days until expiry
			days_until_expiry = (passport_expiry - today_date).days
			
			if days_until_expiry < 0:
				# Already expired
				message = _(
					"⚠️ WARNING: Applicant's Passport has already EXPIRED on {0}. "
					"Please ensure passport is renewed before proceeding."
				).format(frappe.format(applicant_doc.passport_expiry_date, {"fieldtype": "Date"}))
			else:
				# Expires soon
				message = _(
					"⚠️ WARNING: Applicant's Passport will expire in {0} days (on {1}). "
					"Please ensure passport is renewed before deployment."
				).format(
					days_until_expiry,
					frappe.format(applicant_doc.passport_expiry_date, {"fieldtype": "Date"})
				)
			
			return {
				"has_warning": True,
				"message": message,
				"expiry_date": str(applicant_doc.passport_expiry_date),
				"days_until_expiry": days_until_expiry
			}
		
		return {"has_warning": False}

	@frappe.whitelist()
	def get_current_stage_name(self):
		"""Return the stage_name of the current Pipeline Stage (for Company-side button visibility)."""
		if not self.get("current_stage"):
			return None
		return frappe.db.get_value("Pipeline Stage", self.current_stage, "stage_name")

	@frappe.whitelist()
	def get_default_Company_interview_round(self):
		"""Return first Interview Round whose name suggests Company/Final round (for pre-fill when adding Company Interview)."""
		return get_default_Company_interview_round()


@frappe.whitelist()
def start_visa_process(job_applicant_name):
	"""
	Standalone whitelisted entry point for Start Visa Process.
	Called from client with full path. Contains full logic so it works even when
	Frappe loads Job Applicant from HRMS (our instance method is not on that class).
	"""
	if not job_applicant_name:
		frappe.throw(_("Job Applicant name is required."), title=_("Validation"))
	ja = frappe.get_doc("Job Applicant", job_applicant_name)
	applicant = ja.get("applicant")
	current_stage = ja.get("current_stage")
	visa_process = ja.get("visa_process")
	if not applicant:
		frappe.throw(_("Applicant is required."), title=_("Validation"))
	if not current_stage:
		frappe.throw(
			_("Pipeline stage is not set. Please set Pipeline and Current Stage first."),
			title=_("Validation"),
		)
	stage_name = frappe.db.get_value("Pipeline Stage", current_stage, "stage_name")
	if stage_name != "Offer Letter Accepted":
		frappe.throw(
			_("Start Visa Process is only allowed when Current Stage is 'Offer Letter Accepted'."),
			title=_("Invalid Stage"),
		)
	if visa_process:
		frappe.throw(
			_("Visa Process already created: {0}").format(visa_process),
			title=_("Already Started"),
		)
	visa_default = get_default_pipeline_and_first_stage("Visa Process")
	if not visa_default:
		frappe.throw(
			_("Visa Process pipeline not found. Please run 'Setup Pipelines and Stages' first."),
			title=_("Setup Required"),
		)
	visa_doc = frappe.get_doc(
		{
			"doctype": "Visa Process",
			"job_applicant": job_applicant_name,
			"applicant": applicant,
			"pipeline": visa_default["pipeline"],
			"current_stage": visa_default["current_stage"],
			"started_on": today(),
		}
	)
	visa_doc.insert(ignore_permissions=True)
	# Link Visa Process to Job Applicant and set Job Applicant to Visa Process pipeline + first stage (Medical)
	frappe.db.set_value("Job Applicant", job_applicant_name, "visa_process", visa_doc.name, update_modified=False)
	frappe.db.set_value("Job Applicant", job_applicant_name, "pipeline", visa_default["pipeline"], update_modified=False)
	frappe.db.set_value("Job Applicant", job_applicant_name, "current_stage", visa_default["current_stage"], update_modified=False)
	frappe.db.commit()
	return {
		"success": True,
		"visa_process": visa_doc.name,
		"message": _("Visa Process {0} created.").format(visa_doc.name),
	}


def sync_job_applicant_stage_to_visa_process(doc, method=None):
	"""
	Doc event handler: when Job Applicant is saved with pipeline "Visa Process"
	and a linked Visa Process, keep Visa Process's pipeline and current_stage
	in sync with Job Applicant. Uses db.set_value to avoid triggering Visa Process
	on_update (no sync loop). Works regardless of which Job Applicant controller is used (HRMS vs app).
	"""
	if doc.doctype != "Job Applicant":
		return
	if not doc.get("visa_process") or not doc.get("pipeline") or doc.pipeline != "Visa Process":
		return
	if not doc.get("current_stage"):
		return
	vp_name = doc.visa_process
	frappe.db.set_value("Visa Process", vp_name, "pipeline", doc.pipeline, update_modified=False)
	frappe.db.set_value("Visa Process", vp_name, "current_stage", doc.current_stage, update_modified=False)
	frappe.db.commit()


@frappe.whitelist()
def get_default_Company_interview_round():
	"""
	Return first Interview Round whose name suggests Company/Final round (for pre-fill when adding Company Interview).
	Standalone so Company can call via full path; Job Applicant doctype may resolve to HRMS controller.
	"""
	rounds = frappe.get_all(
		"Interview Round",
		fields=["name", "round_name"],
		order_by="creation asc",
	)
	for r in rounds:
		name = (r.get("round_name") or "").lower()
		if "Company" in name or "final" in name or "company" in name:
			return r.get("name")
	return None


@frappe.whitelist()
def get_first_stage_for_pipeline(pipeline_name):
	"""
	Return the first Pipeline Stage name (by sequence) for a pipeline. From DB only.
	Used by Company when pipeline changes to auto-set Current Stage to first stage.
	"""
	first = get_first_stage_for_pipeline_name(pipeline_name)
	return first


@frappe.whitelist()
def get_initial_pipeline_and_stage():
	"""
	Return default pipeline and its first stage for Job Applicant (from DB: first active
	Pipeline where applies_to = "Job Applicant" and first Pipeline Stage by sequence).
	Used by Company script when "Ready for Application Pipeline" is checked.
	"""
	default = get_default_pipeline_and_first_stage("Job Applicant")
	if not default:
		return {"pipeline": None, "current_stage": None}
	return default


@frappe.whitelist()
def get_stage_name(stage_link_value):
	"""Return stage_name for a Pipeline Stage (by link value). Used by client to populate current_stage_name so depends_on works."""
	if not stage_link_value:
		return None
	return frappe.db.get_value("Pipeline Stage", stage_link_value, "stage_name")


@frappe.whitelist()
def get_job_applicant_current_stage_name(name):
	"""Return current stage name for a Job Applicant (for Company script)."""
	if not name:
		return None
	current_stage = frappe.db.get_value("Job Applicant", name, "current_stage")
	if not current_stage:
		return None
	return frappe.db.get_value("Pipeline Stage", current_stage, "stage_name")


@frappe.whitelist()
def get_job_applicant_pipeline_context(job_applicant_name):
	"""Return pipeline and current stage name for a Job Applicant (for Interview form context)."""
	if not job_applicant_name:
		return {"pipeline": None, "current_stage_name": None}
	pipeline = frappe.db.get_value("Job Applicant", job_applicant_name, "pipeline")
	current_stage = frappe.db.get_value("Job Applicant", job_applicant_name, "current_stage")
	current_stage_name = None
	if current_stage:
		current_stage_name = frappe.db.get_value("Pipeline Stage", current_stage, "stage_name")
	return {"pipeline": pipeline, "current_stage_name": current_stage_name}


@frappe.whitelist()
def get_passport_expiry_warning(name, applicant=None):
	"""
	Standalone whitelisted function to get passport expiry warning
	This is called from JavaScript
	
	Parameters:
		name: Job Applicant document name
		applicant: Optional Applicant name (for direct checking)
	
	Returns: Dictionary with has_warning (bool) and message (str) if warning exists
	"""
	try:
		# If applicant is provided directly, use it; otherwise get from Job Applicant
		if applicant:
			applicant_name = applicant
		else:
			job_applicant = frappe.get_doc("Job Applicant", name)
			if not job_applicant.applicant:
				return {"has_warning": False}
			applicant_name = job_applicant.applicant
		
		# Get Applicant document
		applicant_doc = frappe.get_doc("Applicant", applicant_name)
		
		# Check if passport expiry date exists
		if not applicant_doc.passport_expiry_date:
			return {"has_warning": False}
		
		# Calculate 6 months from today
		today_date = getdate(today())
		six_months_from_today = add_months(today_date, 6)
		passport_expiry = getdate(applicant_doc.passport_expiry_date)
		
		# Check if passport expires within 6 months
		if passport_expiry < six_months_from_today:
			# Calculate days until expiry
			days_until_expiry = (passport_expiry - today_date).days
			
			if days_until_expiry < 0:
				# Already expired
				message = _(
					"⚠️ WARNING: Applicant's Passport has already EXPIRED on {0}. "
					"Please ensure passport is renewed before proceeding."
				).format(frappe.format(applicant_doc.passport_expiry_date, {"fieldtype": "Date"}))
			else:
				# Expires soon
				message = _(
					"⚠️ WARNING: Applicant's Passport will expire in {0} days (on {1}). "
					"Please ensure passport is renewed before deployment."
				).format(
					days_until_expiry,
					frappe.format(applicant_doc.passport_expiry_date, {"fieldtype": "Date"})
				)
			
			return {
				"has_warning": True,
				"message": message,
				"expiry_date": str(applicant_doc.passport_expiry_date),
				"days_until_expiry": days_until_expiry
			}
		
		return {"has_warning": False}
		
	except frappe.DoesNotExistError:
		return {"has_warning": False}
	except Exception as e:
		frappe.log_error(
			f"Error in get_passport_expiry_warning for {name}: {str(e)}\n{frappe.get_traceback()}",
			"Passport Expiry Warning Error"
		)
		return {"has_warning": False}


# create_application_from_job_applicant removed: Application doctype has been removed.
# Pipeline and stages are managed on Job Applicant.
