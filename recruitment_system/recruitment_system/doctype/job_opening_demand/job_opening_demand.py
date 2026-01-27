# Copyright (c) 2026, abdullahjavaid198@gmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


@frappe.whitelist()
def get_demand_positions(demand_name):
	"""
	Fetch Demand Positions from a Demand for Job Opening
	
	Args:
		demand_name: Demand document name
		
	Returns:
		List of dictionaries with job_title and position data
	"""
	if not demand_name:
		return []
	
	try:
		if not frappe.db.exists("Demand", demand_name):
			frappe.throw(_("Demand {0} does not exist").format(demand_name))
		
		demand = frappe.get_doc("Demand", demand_name)
		
		positions = []
		if hasattr(demand, 'positions') and demand.positions:
			for position in demand.positions:
				if position.job_title:
					positions.append({
						"job_title": position.job_title,
						"name": position.name,
						"quantity": position.quantity or 0,
						"experience_required": position.experience_required or "",
						"education_required": position.education_required or "",
						"job_category": position.job_category or "",
						"basic_sallary": position.basic_sallary or "",
						"remarks": position.remarks or ""
					})
		
		return positions
		
	except frappe.DoesNotExistError:
		frappe.log_error(
			f"Demand {demand_name} not found",
			"Job Opening Demand - Demand Not Found"
		)
		return []
	except Exception as e:
		frappe.log_error(
			f"Error fetching Demand Positions for Demand {demand_name}: {str(e)}\n{frappe.get_traceback()}",
			"Job Opening Demand - Get Positions Error"
		)
		return []


@frappe.whitelist()
def get_demand_position_details(demand_name, position_job_title):
	"""
	Get specific Demand Position details by job_title
	
	Args:
		demand_name: Demand document name
		position_job_title: Job title from Demand Position
		
	Returns:
		Dictionary with position details or None
	"""
	if not demand_name or not position_job_title:
		return None
	
	try:
		positions = get_demand_positions(demand_name)
		
		for position in positions:
			if position.get("job_title") == position_job_title:
				return position
		
		return None
		
	except Exception as e:
		frappe.log_error(
			f"Error fetching Demand Position details for {position_job_title} in Demand {demand_name}: {str(e)}\n{frappe.get_traceback()}",
			"Job Opening Demand - Get Position Details Error"
		)
		return None


@frappe.whitelist()
def get_demand_age_requirements(demand_name):
	"""
	Get age_min and age_max from Demand level
	
	Args:
		demand_name: Demand document name
		
	Returns:
		Dictionary with age_min and age_max
	"""
	if not demand_name:
		return {}
	
	try:
		demand = frappe.get_doc("Demand", demand_name)
		return {
			"age_min": demand.age_min or None,
			"age_max": demand.age_max or None
		}
	except Exception as e:
		frappe.log_error(
			f"Error fetching age requirements for Demand {demand_name}: {str(e)}",
			"Job Opening Demand - Get Age Requirements Error"
		)
		return {}
