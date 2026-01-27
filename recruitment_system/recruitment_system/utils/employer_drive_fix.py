# Copyright (c) 2026, abdullahjavaid198@gmail.com and contributors
# For license information, please see license.txt

"""
Utility script to fix Drive folders for existing Employer records.

Usage:
    bench --site [site-name] console
    >>> from recruitment_system.recruitment_system.recruitment_system.utils.employer_drive_fix import fix_all_employers
    >>> fix_all_employers()
"""

import frappe
from frappe import _


@frappe.whitelist()
def fix_all_employers():
	"""
	Function: fix_all_employers
	Purpose: Create Drive folders for all existing Employer records that don't have folders
	Returns: Dictionary with results
	"""
	results = {
		"total": 0,
		"success": 0,
		"failed": 0,
		"errors": []
	}
	
	try:
		# Get all Employers
		employers = frappe.get_all(
			"Employer",
			filters={},
			fields=["name", "employer_name"]
		)
		
		results["total"] = len(employers)
		
		for employer_data in employers:
			employer_name = employer_data.get("employer_name")
			employer_id = employer_data.get("name")
			
			if not employer_name:
				results["failed"] += 1
				results["errors"].append({
					"employer": employer_id,
					"error": "Employer name is missing"
				})
				continue
			
			try:
				# Get Employer document
				employer = frappe.get_doc("Employer", employer_id)
				
				# Create folder structure
				success = employer.create_employer_drive_structure()
				
				if success:
					results["success"] += 1
					frappe.db.commit()
				else:
					results["failed"] += 1
					results["errors"].append({
						"employer": employer_id,
						"employer_name": employer_name,
						"error": "Folder creation returned False. Check Error Log for details."
					})
					
			except Exception as e:
				results["failed"] += 1
				error_msg = str(e)
				results["errors"].append({
					"employer": employer_id,
					"employer_name": employer_name,
					"error": error_msg
				})
				frappe.log_error(
					f"Error creating Drive folders for Employer {employer_id} ({employer_name}): {error_msg}\n{frappe.get_traceback()}",
					"Employer Drive Folder Fix Error"
				)
		
		return results
		
	except Exception as e:
		frappe.log_error(
			f"Error in fix_all_employers: {str(e)}\n{frappe.get_traceback()}",
			"Employer Drive Folder Fix Error"
		)
		results["errors"].append({
			"error": f"Fatal error: {str(e)}"
		})
		return results


@frappe.whitelist()
def fix_single_employer(employer_name):
	"""
	Function: fix_single_employer
	Purpose: Create Drive folders for a single Employer by name
	Parameters:
		- employer_name: Name or ID of the Employer
	Returns: Dictionary with success status and message
	"""
	try:
		# Try to get by name first, then by ID
		if frappe.db.exists("Employer", employer_name):
			employer = frappe.get_doc("Employer", employer_name)
		else:
			# Try to find by employer_name field
			employer_id = frappe.db.get_value("Employer", {"employer_name": employer_name}, "name")
			if not employer_id:
				return {
					"success": False,
					"message": _("Employer not found: {0}").format(employer_name)
				}
			employer = frappe.get_doc("Employer", employer_id)
		
		if not employer.employer_name:
			return {
				"success": False,
				"message": _("Employer name is missing for {0}").format(employer.name)
			}
		
		# Create folder structure
		success = employer.create_employer_drive_structure()
		
		if success:
			frappe.db.commit()
			return {
				"success": True,
				"message": _("Drive folders created successfully for {0}").format(employer.employer_name)
			}
		else:
			return {
				"success": False,
				"message": _("Failed to create Drive folders. Please check Error Log for details.")
			}
			
	except Exception as e:
		frappe.log_error(
			f"Error fixing Employer {employer_name}: {str(e)}\n{frappe.get_traceback()}",
			"Employer Drive Folder Fix Error"
		)
		return {
			"success": False,
			"message": _("Error: {0}").format(str(e))
		}
