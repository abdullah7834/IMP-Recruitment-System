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
			"column_break_18",
			"job_opening_title"  # In case it was added manually
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
			# SECTION: Screening Results
			# ============================================
			{
				"fieldname": "screening_results_section",
				"fieldtype": "Section Break",
				"label": "Screening Results",
				"insert_after": "demand_position"
			},
			{
				"fieldname": "internal_hr_result",
				"fieldtype": "Select",
				"label": "Internal HR Result",
				"options": "Pass\nFail\nHold",
				"insert_after": "screening_results_section"
			},
			{
				"fieldname": "column_break_screening_1",
				"fieldtype": "Column Break",
				"insert_after": "internal_hr_result"
			},
			{
				"fieldname": "technical_result",
				"fieldtype": "Select",
				"label": "Technical Result",
				"options": "Pass\nFail\nHold",
				"insert_after": "column_break_screening_1"
			},
			
			# ============================================
			# SECTION: Pipeline Bridge (Control)
			# ============================================
			{
				"fieldname": "pipeline_bridge_section",
				"fieldtype": "Section Break",
				"label": "Pipeline Bridge (Control)",
				"insert_after": "technical_result"
			},
			{
				"fieldname": "ready_for_pipeline",
				"fieldtype": "Check",
				"label": "Ready for Application Pipeline",
				"default": 0,
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
