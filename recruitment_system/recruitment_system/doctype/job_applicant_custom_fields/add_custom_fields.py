# Copyright (c) 2026, abdullahjavaid198@gmail.com and contributors
# For license information, please see license.txt

"""
Add custom fields to Job Applicant DocType for overseas recruitment.
This script adds minimal, clean fields without duplicating Applicant master data.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def check_field_exists(fieldname, doctype="Job Applicant"):
	"""
	Check if a field already exists in Job Applicant (either standard or custom)
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


@frappe.whitelist()
def update_demand_position_field_type():
	"""
	Update the demand_position field from Data to Select type.
	This is needed when the field was already created as Data type.
	"""
	try:
		# Find the existing custom field
		custom_field_name = frappe.db.exists("Custom Field", {
			"dt": "Job Applicant",
			"fieldname": "demand_position"
		})
		
		if not custom_field_name:
			frappe.msgprint("Custom field 'demand_position' not found. Please add it first.", title="Info")
			return {"status": "error", "message": "Field not found"}
		
		# Get the custom field document
		custom_field = frappe.get_doc("Custom Field", custom_field_name)
		
		# Check current fieldtype
		if custom_field.fieldtype == "Select":
			frappe.msgprint("Field 'demand_position' is already a Select field.", title="Info")
			return {"status": "success", "message": "Already Select type"}
		
		# Update fieldtype to Select
		custom_field.fieldtype = "Select"
		custom_field.options = ""  # Will be populated dynamically via JavaScript
		custom_field.save(ignore_permissions=True)
		
		frappe.db.commit()
		
		# Clear cache
		frappe.clear_cache(doctype="Job Applicant")
		
		frappe.msgprint(
			f"Successfully updated 'demand_position' field from {custom_field.get_doc_before_save().fieldtype} to Select.",
			title="Success"
		)
		
		return {"status": "success", "message": "Field type updated"}
		
	except Exception as e:
		error_msg = f"Error updating field type: {str(e)}\n{frappe.get_traceback()}"
		frappe.log_error(error_msg, "Update Demand Position Field Type Error")
		frappe.msgprint(f"Error updating field type: {str(e)}", title="Error")
		return {"status": "error", "message": str(e)}


@frappe.whitelist()
def remove_existing_job_applicant_custom_fields():
	"""
	Remove all existing custom fields for Job Applicant to avoid duplicates.
	Use this before adding new custom fields.
	"""
	try:
		existing_fields = frappe.get_all(
			"Custom Field",
			filters={"dt": "Job Applicant"},
			fields=["name", "fieldname"]
		)
		
		if existing_fields:
			for field in existing_fields:
				frappe.delete_doc("Custom Field", field.name, force=1)
				frappe.db.commit()
			
			frappe.msgprint(
				f"Removed {len(existing_fields)} existing custom fields for Job Applicant",
				indicator="blue"
			)
			return {"success": True, "removed": len(existing_fields)}
		else:
			return {"success": True, "removed": 0}
	except Exception as e:
		frappe.log_error(
			f"Error removing Job Applicant custom fields: {str(e)}",
			"Remove Custom Fields Error"
		)
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def cleanup_duplicate_job_applicant_custom_fields():
	"""
	Remove duplicate custom fields by fieldname for Job Applicant.
	Keeps only the most recent one.
	"""
	try:
		# Get all custom fields for Job Applicant
		all_fields = frappe.get_all(
			"Custom Field",
			filters={"dt": "Job Applicant"},
			fields=["name", "fieldname", "creation"],
			order_by="creation desc"
		)
		
		# Find duplicates
		seen_fieldnames = {}
		duplicates_to_delete = []
		
		for field in all_fields:
			fieldname = field.get("fieldname")
			if fieldname in seen_fieldnames:
				# This is a duplicate, mark for deletion
				duplicates_to_delete.append(field.name)
			else:
				seen_fieldnames[fieldname] = field.name
		
		# Delete duplicates
		if duplicates_to_delete:
			for field_name in duplicates_to_delete:
				try:
					frappe.delete_doc("Custom Field", field_name, force=1)
				except Exception:
					pass
			
			frappe.db.commit()
			frappe.msgprint(
				f"Removed {len(duplicates_to_delete)} duplicate custom fields",
				indicator="blue"
			)
			return {"success": True, "removed": len(duplicates_to_delete)}
		else:
			return {"success": True, "removed": 0}
	except Exception as e:
		frappe.log_error(
			f"Error cleaning up duplicate Job Applicant custom fields: {str(e)}",
			"Cleanup Duplicates Error"
		)
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def add_custom_fields_to_job_applicant():
	"""
	Add custom fields to Job Applicant doctype for overseas recruitment.
	Fields are organized into logical sections with clean layout (2 fields per row).
	"""
		# Standard fields that already exist - DO NOT add these as custom fields
	existing_standard_fields = [
			"applicant_name",
			"email_id",
			"phone_number",
			"job_title",
			"designation",
			"status",
			"source",
			"column_break_3",
			"column_break_13",
			"column_break_18"
			# Note: job_opening_title is a custom field, not a standard field
		]
	
	custom_fields = {
		"Job Applicant": [
			# ============================================
			# SECTION: Applicant Reference
			# ============================================
			{
				"fieldname": "applicant_reference_section",
				"fieldtype": "Section Break",
				"label": "Applicant Reference",
				"insert_after": "job_title"
			},
			{
				"fieldname": "applicant",
				"fieldtype": "Link",
				"label": "Applicant (Master)",
				"options": "Applicant",
				"reqd": 1,
				"insert_after": "applicant_reference_section"
			},
			
			# ============================================
			# SECTION: Demand Context
			# ============================================
			{
				"fieldname": "demand_context_section",
				"fieldtype": "Section Break",
				"label": "Demand Context",
				"insert_after": "applicant"
			},
			{
				"fieldname": "linked_demand",
				"fieldtype": "Link",
				"label": "Linked Demand",
				"options": "Demand",
				"insert_after": "demand_context_section"
			},
			{
				"fieldname": "column_break_demand_1",
				"fieldtype": "Column Break",
				"insert_after": "linked_demand"
			},
			{
				"fieldname": "demand_position",
				"fieldtype": "Select",
				"label": "Demand Position",
				"insert_after": "column_break_demand_1"
			},
			{
				"fieldname": "job_opening_title",
				"fieldtype": "Data",
				"label": "Job Opening Title",
				"read_only": 1,
				"insert_after": "demand_position"
			},
			
			# ============================================
			# SECTION: Pipeline Bridge (Control)
			# ============================================
			{
				"fieldname": "pipeline_bridge_section",
				"fieldtype": "Section Break",
				"label": "Pipeline Bridge (Control)",
				"insert_after": "job_opening_title"
			},
			{
				"fieldname": "ready_for_pipeline",
				"fieldtype": "Check",
				"label": "Ready for Application Pipeline",
				"default": 0,
				"description": "When checked, Pipeline is set to Interviews and Current Stage to Screening (first stage). Save after checking to persist.",
				"insert_after": "pipeline_bridge_section"
			},
			{
				"fieldname": "column_break_pipeline_1",
				"fieldtype": "Column Break",
				"insert_after": "ready_for_pipeline"
			},
			{
				"fieldname": "converted_to_application",
				"fieldtype": "Check",
				"label": "Converted to Application",
				"read_only": 1,
				"default": 0,
				"insert_after": "column_break_pipeline_1"
			},
			# ============================================
			# SECTION: Pipeline & Stages
			# ============================================
			{
				"fieldname": "pipeline_section",
				"fieldtype": "Section Break",
				"label": "Pipeline & Stages",
				"insert_after": "converted_to_application"
			},
			{
				"fieldname": "pipeline",
				"fieldtype": "Link",
				"label": "Pipeline",
				"options": "Pipeline",
				"insert_after": "pipeline_section"
			},
			{
				"fieldname": "current_stage",
				"fieldtype": "Link",
				"label": "Current Stage",
				"options": "Pipeline Stage",
				"insert_after": "pipeline"
			},
			{
				"fieldname": "current_stage_name",
				"fieldtype": "Data",
				"label": "Current Stage Name",
				"read_only": 1,
				"hidden": 1,
				"fetch_from": "current_stage.stage_name",
				"insert_after": "current_stage"
			},
			{
				"fieldname": "column_break_pl",
				"fieldtype": "Column Break",
				"insert_after": "current_stage_name"
			},
			# Company Selection Date: show when Company Selected / Offer Letter / Visa Process (historical); hide only when Interviews + Screening
			{
				"fieldname": "Company_selection_date",
				"fieldtype": "Date",
				"label": "Company Selection Date",
				"insert_after": "column_break_pl",
				"depends_on": "eval:(doc.current_stage_name == 'Company Selected' || doc.pipeline == 'Offer Letter' || doc.visa_process) && !(doc.pipeline == 'Interviews' && doc.current_stage_name == 'Screening')"
			},
			# Offer Letter Received Date: show when Offer Letter pipeline (editable) or Visa Process linked (historical); hide when Interviews + Screening
			{
				"fieldname": "offer_letter_received_date",
				"fieldtype": "Date",
				"label": "Offer Letter Received Date",
				"insert_after": "Company_selection_date",
				"depends_on": "eval:(doc.pipeline == 'Offer Letter' && ['Offer Letter Received', 'Offer Letter Accepted'].includes(doc.current_stage_name) || doc.visa_process) && !(doc.pipeline == 'Interviews' && doc.current_stage_name == 'Screening')"
			},
			# Offer Letter Accepted Date: show when Offer Letter + stage Accepted (editable) or Visa Process linked (historical); hide when Interviews + Screening
			{
				"fieldname": "offer_letter_accepted_date",
				"fieldtype": "Date",
				"label": "Offer Letter Accepted Date",
				"insert_after": "offer_letter_received_date",
				"depends_on": "eval:(doc.pipeline == 'Offer Letter' && doc.current_stage_name == 'Offer Letter Accepted' || doc.visa_process) && !(doc.pipeline == 'Interviews' && doc.current_stage_name == 'Screening')"
			},
			{
				"fieldname": "visa_process",
				"fieldtype": "Link",
				"label": "Visa Process",
				"options": "Visa Process",
				"read_only": 1,
				"insert_after": "offer_letter_accepted_date",
				"depends_on": "eval:doc.pipeline == 'Offer Letter' || doc.visa_process"
			}
		]
	}
	
	try:
		# First, clean up any duplicate custom fields
		cleanup_duplicate_job_applicant_custom_fields()
		
		# Filter out fields that already exist (standard or custom)
		fields_to_add = []
		skipped_fields = []
		
		for field in custom_fields["Job Applicant"]:
			fieldname = field.get("fieldname")
			
			# Skip if it's in the list of existing standard fields
			if fieldname in existing_standard_fields:
				skipped_fields.append(f"{fieldname} (standard field)")
				continue
			
			# Check if field already exists
			if check_field_exists(fieldname, "Job Applicant"):
				skipped_fields.append(f"{fieldname} (already exists)")
				continue
			
			# Add field to list
			fields_to_add.append(field)
		
		# Create custom fields
		if fields_to_add:
			create_custom_fields(
				{"Job Applicant": fields_to_add},
				ignore_validate=True,
				update=True
			)
			
			frappe.db.commit()
			
			message = f"Successfully added {len(fields_to_add)} custom fields to Job Applicant"
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
		error_msg = f"Error adding custom fields to Job Applicant: {str(e)}"
		frappe.log_error(error_msg, "Add Custom Fields Error")
		frappe.msgprint(error_msg, indicator="red")
		return {"success": False, "error": str(e)}


# Depends-on expressions: show dates when Offer Letter or Visa Process (historical); hide only when Interviews + Screening
_DATE_FIELDS_DEPENDS_ON = {
	"Company_selection_date": "eval:(doc.current_stage_name == 'Company Selected' || doc.pipeline == 'Offer Letter' || doc.visa_process) && !(doc.pipeline == 'Interviews' && doc.current_stage_name == 'Screening')",
	"offer_letter_received_date": "eval:(doc.pipeline == 'Offer Letter' && ['Offer Letter Received', 'Offer Letter Accepted'].includes(doc.current_stage_name) || doc.visa_process) && !(doc.pipeline == 'Interviews' && doc.current_stage_name == 'Screening')",
	"offer_letter_accepted_date": "eval:(doc.pipeline == 'Offer Letter' && doc.current_stage_name == 'Offer Letter Accepted' || doc.visa_process) && !(doc.pipeline == 'Interviews' && doc.current_stage_name == 'Screening')",
}


@frappe.whitelist()
def update_date_fields_depends_on():
	"""
	Update the depends_on of Company Selection Date, Offer Letter Received Date, and Offer Letter Accepted Date
	so they are hidden only when Pipeline is Interviews and Current Stage is Screening, and so they remain
	visible when pipeline is Visa Process (historical; read-only via client script).
	Run once after changing the logic in add_custom_fields.py so existing Custom Field records are updated.
	"""
	try:
		updated = []
		for fieldname, depends_on in _DATE_FIELDS_DEPENDS_ON.items():
			name = frappe.db.exists("Custom Field", {"dt": "Job Applicant", "fieldname": fieldname})
			if name:
				doc = frappe.get_doc("Custom Field", name)
				doc.depends_on = depends_on
				doc.save(ignore_permissions=True)
				updated.append(fieldname)
		frappe.db.commit()
		frappe.clear_cache(doctype="Job Applicant")
		if updated:
			frappe.msgprint(
				f"Updated depends_on for: {', '.join(updated)}. Clear cache and reload the form.",
				indicator="green",
			)
		return {"success": True, "updated": updated}
	except Exception as e:
		frappe.log_error(f"Update date fields depends_on: {str(e)}", "Update Date Fields Depends On")
		return {"success": False, "error": str(e)}


# Fieldnames removed from Job Applicant (Screening Results section)
_SCREENING_RESULTS_FIELDS = (
	"screening_results_section",
	"internal_hr_result",
	"column_break_screening_1",
	"technical_result",
)


@frappe.whitelist()
def remove_screening_results_fields():
	"""
	Remove the Screening Results section and its fields (Internal HR Result, Technical Result)
	from the Job Applicant form. Run once if those custom fields already exist in the database.
	"""
	try:
		removed = []
		for fieldname in _SCREENING_RESULTS_FIELDS:
			name = frappe.db.exists("Custom Field", {"dt": "Job Applicant", "fieldname": fieldname})
			if name:
				frappe.delete_doc("Custom Field", name, force=1)
				removed.append(fieldname)
		frappe.db.commit()
		frappe.clear_cache(doctype="Job Applicant")
		if removed:
			frappe.msgprint(
				f"Removed Screening Results fields: {', '.join(removed)}. Clear cache and reload the form.",
				indicator="blue",
			)
		return {"success": True, "removed": removed}
	except Exception as e:
		frappe.log_error(f"Remove screening results fields: {str(e)}", "Remove Screening Results Fields")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_job_applicant_existing_fields():
	"""
	Get all existing fields in Job Applicant doctype (both standard and custom).
	Use this to understand which fields already exist before adding custom fields.
	"""
	try:
		# Get standard fields from DocType
		meta = frappe.get_meta("Job Applicant")
		standard_fields = []
		for field in meta.fields:
			standard_fields.append({
				"fieldname": field.fieldname,
				"fieldtype": field.fieldtype,
				"label": field.label or "",
				"is_custom": 0
			})
		
		# Get custom fields
		custom_fields = frappe.get_all(
			"Custom Field",
			filters={"dt": "Job Applicant"},
			fields=["name", "fieldname", "fieldtype", "label", "insert_after", "creation"],
			order_by="creation asc"
		)
		
		# Check for duplicates in custom fields
		fieldname_count = {}
		duplicates = []
		for cf in custom_fields:
			fn = cf.get("fieldname")
			if fn in fieldname_count:
				fieldname_count[fn] += 1
				duplicates.append(fn)
			else:
				fieldname_count[fn] = 1
		
		result = {
			"standard_fields": standard_fields,
			"custom_fields": custom_fields,
			"standard_field_count": len(standard_fields),
			"custom_field_count": len(custom_fields),
			"duplicates": list(set(duplicates))
		}
		
		# Print summary
		print("\n=== JOB APPLICANT FIELD SUMMARY ===")
		print(f"Standard fields: {len(standard_fields)}")
		print(f"Custom fields: {len(custom_fields)}")
		if duplicates:
			print(f"DUPLICATES FOUND: {list(set(duplicates))}")
		
		print("\n--- Standard Fields ---")
		for f in standard_fields:
			print(f"  {f['fieldname']} ({f['fieldtype']})")
		
		print("\n--- Custom Fields ---")
		for f in custom_fields:
			print(f"  {f['fieldname']} ({f['fieldtype']}) - name: {f['name']}")
		
		return result
		
	except Exception as e:
		frappe.log_error(f"Error getting Job Applicant fields: {str(e)}", "Get Fields Error")
		return {"error": str(e)}


@frappe.whitelist()
def get_applicant_details(applicant_id):
	"""
	Fetch Applicant details for auto-populating Job Applicant fields.
	
	Parameters:
		- applicant_id: CNIC or name of the Applicant record
	
	Returns:
		Dictionary with:
		- full_name: Applicant's full name
		- email_address: Applicant's email address
		- mobile_number: Applicant's mobile number
	"""
	try:
		if not applicant_id:
			return {}
		
		# Get Applicant document
		applicant = frappe.get_doc("Applicant", applicant_id)
		
		# Get field names dynamically to avoid hardcoding
		meta = frappe.get_meta("Applicant")
		
		# Get full_name field
		full_name_field = meta.get_field("full_name").fieldname if meta.get_field("full_name") else "full_name"
		full_name = applicant.get(full_name_field) or ""
		
		# Get email_address field
		email_field = meta.get_field("email_address").fieldname if meta.get_field("email_address") else "email_address"
		email_address = applicant.get(email_field) or ""
		
		# Get mobile_number field
		mobile_field = meta.get_field("mobile_number").fieldname if meta.get_field("mobile_number") else "mobile_number"
		mobile_number = applicant.get(mobile_field) or ""
		
		return {
			"full_name": full_name,
			"email_address": email_address,
			"mobile_number": mobile_number
		}
		
	except frappe.DoesNotExistError:
		frappe.log_error(
			f"Applicant {applicant_id} not found",
			"Get Applicant Details Error"
		)
		return {}
	except Exception as e:
		frappe.log_error(
			f"Error fetching Applicant details for {applicant_id}: {str(e)}\n{frappe.get_traceback()}",
			"Get Applicant Details Error"
		)
		return {}


@frappe.whitelist()
def get_job_opening_by_demand_position(demand_name, demand_position):
	"""
	Find Job Opening that matches the given demand and position.
	
	Parameters:
		- demand_name: Demand document name
		- demand_position: Demand position (job_title from Demand Positions)
	
	Returns:
		Dictionary with job_opening name and job_title if found, None otherwise
	"""
	if not demand_name or not demand_position:
		return None
	
	try:
		# Search for Job Opening with matching linked_demand and demand_position
		job_openings = frappe.get_all(
			"Job Opening",
			filters={
				"linked_demand": demand_name,
				"demand_position": demand_position
			},
			fields=["name", "job_title", "status"],
			limit=1
		)
		
		if job_openings and len(job_openings) > 0:
			job_opening = job_openings[0]
			# Return with job_title (the Job Opening's title field)
			return {
				"name": job_opening.name,
				"job_title": job_opening.job_title or "",
				"status": job_opening.status or ""
			}
		
		return None
		
	except Exception as e:
		frappe.log_error(
			f"Error finding Job Opening for Demand {demand_name}, Position {demand_position}: {str(e)}\n{frappe.get_traceback()}",
			"Get Job Opening by Demand Position Error"
		)
		return None
