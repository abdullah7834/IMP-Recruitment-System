# Copyright (c) 2026, abdullahjavaid198@gmail.com and contributors
# For license information, please see license.txt

"""
Custom Job Opening controller with Drive folder management.
Overrides the standard Job Opening class to add Drive integration.
"""

import frappe
from frappe import _
from hrms.hr.doctype.job_opening.job_opening import JobOpening as BaseJobOpening


class JobOpening(BaseJobOpening):
	"""
	Custom Job Opening class that extends the base HRMS Job Opening.
	Adds Drive folder management functionality.
	"""
	
	def after_insert(self):
		"""
		Function: after_insert
		Purpose: Create Drive folder structure when Job Opening is first created
		Operation: Calls create_job_opening_drive_structure() to set up folder and text file
		Trigger: Called automatically after document is inserted into database
		"""
		# Call parent after_insert if it exists
		if hasattr(super(), 'after_insert'):
			try:
				super().after_insert()
			except Exception:
				pass
		
		# Create Drive folder structure (non-blocking)
		if self.linked_demand:
			try:
				frappe.msgprint(f"[DEBUG] after_insert: Creating Drive structure for {self.name}", indicator="blue", alert=True)
				result = self.create_job_opening_drive_structure()
				if not result:
					frappe.msgprint(f"[DEBUG] FAILED: Drive structure creation returned False for {self.name}", indicator="red", alert=True)
					frappe.log_error(
						f"Failed to create Drive structure for Job Opening {self.name}",
						"Job Opening Drive Creation Warning"
					)
				else:
					frappe.msgprint(f"[DEBUG] SUCCESS: Drive structure created for {self.name}", indicator="green", alert=True)
			except Exception as e:
				frappe.msgprint(f"[DEBUG] EXCEPTION in after_insert: {str(e)}", indicator="red", alert=True)
				frappe.log_error(
					f"Exception in after_insert for Job Opening {self.name}: {str(e)}\n{frappe.get_traceback()}",
					"Job Opening After Insert Error"
				)
	
	def on_update(self):
		"""
		Function: on_update
		Purpose: Handle folder updates and text file regeneration
		Operation:
			- Updates job_opening_details.txt if relevant fields changed
			- Handles Demand Position changes (creates new folder, keeps old)
			- Ensures folder structure exists
		Trigger: Called automatically when document is updated
		"""
		# Call parent on_update
		if hasattr(super(), 'on_update'):
			try:
				super().on_update()
			except Exception:
				pass
		
		if not self.linked_demand:
			return
		
		# Check if Demand Position changed - create new folder (keep old for audit)
		if self.has_value_changed("demand_position") and self.demand_position:
			# Create new folder with updated position name
			self.create_job_opening_drive_structure()
		else:
			# Ensure folder exists (in case it wasn't created on insert)
			job_opening_folder = self.get_job_opening_drive_folder()
			if not job_opening_folder:
				# Folder doesn't exist, create structure
				self.create_job_opening_drive_structure()
			else:
				# Always update text file on update (to ensure it exists and is current)
				self.update_job_opening_txt_file()
	
	def on_trash(self):
		"""
		Function: on_trash
		Purpose: Handle Job Opening deletion
		Operation: Does NOT delete Drive folder (for audit/history)
		Trigger: Called automatically before document is deleted from database
		"""
		# Call parent on_trash if it exists
		if hasattr(super(), 'on_trash'):
			try:
				super().on_trash()
			except Exception:
				pass
		
		# Do NOT delete Drive folder - keep for audit/history
		# Folder remains in Drive for reference
	
	def create_job_opening_drive_structure(self):
		"""
		Function: create_job_opening_drive_structure
		Purpose: Create the complete Drive folder structure for a Job Opening
		Operation:
			1. Validate linked_demand exists
			2. Get Demand's Drive folder
			3. Ensure /Job_Openings/ subfolder exists
			4. Create /Job_Openings/{Job Opening Folder}/
			5. Generate job_opening_details.txt
			6. Save drive_folder_path and drive_folder_url
		Returns: True if successful, False otherwise
		"""
		if not self.linked_demand:
			return False
		
		if not self.name:
			# Document not saved yet, skip
			return False
		
		try:
			# Check if Drive app is installed
			if not frappe.db.exists("DocType", "Drive File"):
				frappe.log_error(
					"Drive app is not installed. Please install the Drive app to enable folder creation.",
					"Job Opening Drive Folder Creation Error"
				)
				return False
			
			# Get linked Demand
			try:
				demand = frappe.get_doc("Demand", self.linked_demand)
			except frappe.DoesNotExistError:
				frappe.log_error(
					f"Demand {self.linked_demand} not found for Job Opening {self.name}",
					"Job Opening Drive Folder Creation Error"
				)
				return False
			
			# Get Demand's Drive folder
			demand_folder = demand.get_demand_drive_folder()
			if not demand_folder:
				# Try to create Demand folder structure first
				demand.create_demand_drive_structure()
				demand_folder = demand.get_demand_drive_folder()
				if not demand_folder:
					frappe.log_error(
						f"Cannot find or create Drive folder for Demand {self.linked_demand}",
						"Job Opening Drive Folder Creation Error"
					)
					return False
			
			# Get Employer to use its helper methods
			if not demand.employer:
				frappe.log_error(
					f"Demand {self.linked_demand} has no linked Employer",
					"Job Opening Drive Folder Creation Error"
				)
				return False
			
			try:
				employer = frappe.get_doc("Employer", demand.employer)
			except frappe.DoesNotExistError:
				frappe.log_error(
					f"Employer {demand.employer} not found for Job Opening {self.name}",
					"Job Opening Drive Folder Creation Error"
				)
				return False
			
			# Get team
			team = employer.get_drive_team()
			if not team:
				frappe.log_error(
					f"No Drive team found for Job Opening {self.name}",
					"Job Opening Drive Folder Creation Error"
				)
				return False
			
			# Step 1: Ensure /Job_Openings/ subfolder exists under Demand folder
			job_openings_folder = self.ensure_job_openings_root(demand_folder, team, employer)
			if not job_openings_folder:
				frappe.log_error(
					f"Failed to create/get 'Job_Openings' folder in Demand folder '{demand_folder}' for team '{team}'",
					"Job Opening Drive Folder Creation Error"
				)
				return False
			
			# Step 2: Build Job Opening folder name
			# Format: "{job_title}_{demand_position}" or just "{job_title}" if no position
			folder_name = self.get_job_opening_folder_name()
			
			# Check if folder already exists (reuse existing folder)
			existing_folder = self.get_drive_folder_by_title(folder_name, job_openings_folder, team)
			
			if existing_folder:
				# Folder already exists, reuse it
				job_opening_folder = existing_folder
			else:
				# Step 3: Create /Job_Openings/{Job Opening Folder}/ folder
				job_opening_folder = employer.get_or_create_drive_folder(folder_name, job_openings_folder, team)
				if not job_opening_folder:
					frappe.log_error(
						f"Failed to create Job Opening folder '{folder_name}' in 'Job_Openings' folder for team '{team}'",
						"Job Opening Drive Folder Creation Error"
					)
					return False
			
			# Step 4: Generate job_opening_details.txt
			try:
				frappe.msgprint(f"[DEBUG] Step 4: Generating txt file for {self.name} in folder {job_opening_folder}", indicator="blue", alert=True)
				self.generate_job_opening_txt_file(job_opening_folder, team, employer, demand)
				frappe.msgprint(f"[DEBUG] Step 4: Completed txt file generation for {self.name}", indicator="green", alert=True)
			except Exception as e:
				frappe.msgprint(f"[DEBUG] Step 4 FAILED: {str(e)}", indicator="red", alert=True)
				frappe.log_error(
					f"Error generating text file for Job Opening {self.name}: {str(e)}\n{frappe.get_traceback()}",
					"Job Opening Text File Generation Error"
				)
				# Don't fail the whole operation if text file creation fails
			
			# Step 5: Save folder references (if fields exist)
			# Use db_set to avoid recursion during insert
			if hasattr(self, 'drive_folder_path') or frappe.db.has_column("Job Opening", "drive_folder_path"):
				try:
					# Get folder path for storage
					meta = frappe.get_meta("Demand")
					demand_title_field = meta.get_field("demand_title").fieldname if meta.get_field("demand_title") else "demand_title"
					demand_reference_no_field = meta.get_field("demand_reference_no").fieldname if meta.get_field("demand_reference_no") else "demand_reference_no"
					
					demand_title_value = demand.get(demand_title_field) or ""
					demand_reference_no_value = demand.get(demand_reference_no_field) or demand.name
					
					demand_folder_name = f"{demand_title_value}-{demand_reference_no_value}" if demand_title_value else demand.name
					
					employer_meta = frappe.get_meta("Employer")
					employer_name_field = employer_meta.get_field("employer_name").fieldname if employer_meta.get_field("employer_name") else "employer_name"
					company_reg_no_field = employer_meta.get_field("company_reg_no").fieldname if employer_meta.get_field("company_reg_no") else "company_reg_no"
					
					employer_name_value = employer.get(employer_name_field) or ""
					company_reg_no_value = employer.get(company_reg_no_field) or ""
					
					employer_folder_name = f"{employer_name_value}-{company_reg_no_value}" if employer_name_value and company_reg_no_value else employer.name
					
					folder_path = f"/Employers/{employer_folder_name}/Demands/{demand_folder_name}/Job_Openings/{folder_name}"
					self.db_set("drive_folder_path", folder_path, update_modified=False)
				except Exception:
					pass
			
			if hasattr(self, 'drive_folder_url') or frappe.db.has_column("Job Opening", "drive_folder_url"):
				try:
					# Generate Drive folder URL (optional)
					folder_url = f"/app/drive/{job_opening_folder}"
					self.db_set("drive_folder_url", folder_url, update_modified=False)
				except Exception:
					pass
			
			return True
			
		except Exception as e:
			# Log detailed error information
			error_details = {
				"job_opening_id": self.name,
				"linked_demand": self.linked_demand,
				"demand_position": self.demand_position,
				"user": frappe.session.user,
				"error": str(e),
				"traceback": frappe.get_traceback()
			}
			frappe.log_error(
				f"Error creating Drive folders for Job Opening {self.name} (Demand: {self.linked_demand}): {str(e)}\n{frappe.get_traceback()}\nDetails: {error_details}",
				"Job Opening Drive Folder Creation Error"
			)
			# Don't throw error - allow Job Opening creation to succeed even if folder creation fails
			return False
	
	def ensure_job_openings_root(self, demand_folder, team, employer):
		"""
		Function: ensure_job_openings_root
		Purpose: Ensure /Job_Openings/ subfolder exists under Demand folder
		Parameters:
			- demand_folder: Demand's Drive folder name
			- team: Drive team name
			- employer: Employer document (to use helper methods)
		Returns: Drive File document name (string) or None
		"""
		try:
			job_openings_folder = employer.get_or_create_drive_folder("Job_Openings", demand_folder, team)
			return job_openings_folder
		except Exception as e:
			frappe.log_error(
				f"Error ensuring Job_Openings root folder: {str(e)}",
				"Job Opening Drive Folder Creation Error"
			)
			return None
	
	def get_job_opening_folder_name(self):
		"""
		Function: get_job_opening_folder_name
		Purpose: Generate folder name for Job Opening
		Format: "{job_title}_{demand_position}" or "{job_title}" if no position
		Returns: Sanitized folder name string
		"""
		# Get field names from meta to avoid hardcoding
		meta = frappe.get_meta("Job Opening")
		job_title_field = meta.get_field("job_title").fieldname if meta.get_field("job_title") else "job_title"
		
		job_title_value = self.get(job_title_field) or self.name
		
		# Get Demand Position name
		demand_position_value = self.get("demand_position") or ""
		
		# Build folder name
		if demand_position_value:
			folder_name = f"{self.name}_{demand_position_value}"
		else:
			folder_name = self.name
		
		# Sanitize folder name (use Employer's sanitize method)
		try:
			demand = frappe.get_doc("Demand", self.linked_demand)
			if demand.employer:
				employer = frappe.get_doc("Employer", demand.employer)
				folder_name = employer.sanitize_folder_name(folder_name)
		except Exception:
			# Fallback sanitization
			folder_name = str(folder_name).replace("/", "-").strip()
		
		# Ensure folder name doesn't exceed limit (140 chars)
		if len(folder_name) > 140:
			folder_name = folder_name[:137] + "..."
		
		return folder_name
	
	def get_job_opening_drive_folder(self):
		"""
		Function: get_job_opening_drive_folder
		Purpose: Get the main Drive folder for this Job Opening
		Operation:
			- Gets Demand folder
			- Finds /Job_Openings/{Job Opening Folder}/ folder
		Returns: Drive File document name (string) or None
		"""
		if not self.name or not self.linked_demand:
			return None
		
		try:
			demand = frappe.get_doc("Demand", self.linked_demand)
			demand_folder = demand.get_demand_drive_folder()
			if not demand_folder:
				return None
			
			# Get Employer to use helper methods
			if not demand.employer:
				return None
			
			employer = frappe.get_doc("Employer", demand.employer)
			team = employer.get_drive_team()
			if not team:
				return None
			
			# Get Job_Openings folder
			job_openings_folder = self.get_drive_folder_by_title("Job_Openings", demand_folder, team)
			if not job_openings_folder:
				return None
			
			# Find Job Opening folder by name
			folder_name = self.get_job_opening_folder_name()
			return self.get_drive_folder_by_title(folder_name, job_openings_folder, team)
			
		except Exception as e:
			frappe.log_error(
				f"Error getting Drive folder for Job Opening {self.name}: {str(e)}",
				"Job Opening Drive Folder Lookup Error"
			)
			return None
	
	def get_drive_folder_by_title(self, title, parent_entity, team):
		"""
		Function: get_drive_folder_by_title
		Purpose: Find a Drive folder by title within a parent folder
		Parameters:
			- title: Folder title to search for
			- parent_entity: Parent Drive File document name
			- team: Drive team name
		Returns: Drive File document name (string) or None
		"""
		return frappe.db.get_value(
			"Drive File",
			{
				"title": title,
				"is_group": 1,
				"is_active": 1,
				"parent_entity": parent_entity,
				"team": team
			},
			"name"
		)
	
	def generate_job_opening_txt_file(self, job_opening_folder, team, employer, demand):
		"""
		Function: generate_job_opening_txt_file
		Purpose: Generate and create job_opening_details.txt file in Drive
		Parameters:
			- job_opening_folder: Job Opening's Drive folder name
			- team: Drive team name
			- employer: Employer document
			- demand: Demand document
		"""
		try:
			# Validate folder exists
			if not job_opening_folder:
				error_msg = f"Job Opening folder is None for Job Opening {self.name}"
				frappe.log_error(error_msg, "Job Opening Text File Generation Error")
				raise ValueError(error_msg)
			
			# Validate team
			if not team:
				error_msg = f"Team is None for Job Opening {self.name}"
				frappe.log_error(error_msg, "Job Opening Text File Generation Error")
				raise ValueError(error_msg)
			
			# Generate file content
			content = self.generate_job_opening_txt_content(employer, demand)
			
			if not content or len(content.strip()) == 0:
				error_msg = f"Generated content is empty for Job Opening {self.name}"
				frappe.log_error(error_msg, "Job Opening Text File Generation Error")
				raise ValueError(error_msg)
			
			# File name
			file_name = "job_opening_details.txt"
			
			# Check if file already exists
			existing_file = frappe.db.get_value(
				"Drive File",
				{
					"title": file_name,
					"parent_entity": job_opening_folder,
					"is_active": 1,
					"is_group": 0,
					"team": team
				},
				"name"
			)
			
			if existing_file:
				# Update existing file
				frappe.log_error(
					f"Updating existing job_opening_details.txt (Drive File: {existing_file}) for Job Opening {self.name}",
					"Job Opening Text File Update",
					is_error=False
				)
				self.update_drive_file_content(existing_file, content, team)
				frappe.db.commit()
			else:
				# Create new file
				frappe.msgprint(f"[DEBUG] File does NOT exist, creating new file in folder {job_opening_folder}", indicator="blue", alert=True)
				frappe.log_error(
					f"Creating new job_opening_details.txt for Job Opening {self.name} in folder {job_opening_folder} (team: {team})",
					"Job Opening Text File Creation",
					is_error=False
				)
				self.create_drive_text_file(file_name, job_opening_folder, content, team)
				# Verify file was created
				frappe.db.commit()
				created_file = frappe.db.get_value(
					"Drive File",
					{
						"title": file_name,
						"parent_entity": job_opening_folder,
						"is_active": 1,
						"is_group": 0,
						"team": team
					},
					"name"
				)
				if created_file:
					frappe.msgprint(f"[DEBUG] SUCCESS: File created and verified! Drive File: {created_file}", indicator="green", alert=True)
					frappe.log_error(
						f"Verified: job_opening_details.txt created successfully (Drive File: {created_file}) for Job Opening {self.name}",
						"Job Opening Text File Creation Success",
						is_error=False
					)
				else:
					frappe.msgprint(f"[DEBUG] WARNING: File creation attempted but NOT found in database!", indicator="orange", alert=True)
					frappe.log_error(
						f"WARNING: File creation attempted but file not found in database for Job Opening {self.name}",
						"Job Opening Text File Creation Warning"
					)
			
		except Exception as e:
			error_msg = f"Error generating job_opening_details.txt for Job Opening {self.name}: {str(e)}\n{frappe.get_traceback()}"
			frappe.log_error(
				error_msg,
				"Job Opening Text File Generation Error"
			)
			# Don't re-raise - allow folder creation to succeed even if file creation fails
			# But log it clearly so user knows
	
	def generate_job_opening_txt_content(self, employer, demand):
		"""
		Function: generate_job_opening_txt_content
		Purpose: Generate formatted text content with Job Opening information
		Parameters:
			- employer: Employer document
			- demand: Demand document
		Returns: Formatted string with Job Opening information
		"""
		from datetime import datetime
		
		# Get field names from meta to avoid hardcoding
		job_opening_meta = frappe.get_meta("Job Opening")
		employer_meta = frappe.get_meta("Employer")
		demand_meta = frappe.get_meta("Demand")
		
		# Get field values
		job_title_field = job_opening_meta.get_field("job_title").fieldname if job_opening_meta.get_field("job_title") else "job_title"
		job_title_value = self.get(job_title_field) or self.name
		
		employer_name_field = employer_meta.get_field("employer_name").fieldname if employer_meta.get_field("employer_name") else "employer_name"
		employer_name_value = employer.get(employer_name_field) or "N/A"
		
		demand_title_field = demand_meta.get_field("demand_title").fieldname if demand_meta.get_field("demand_title") else "demand_title"
		demand_title_value = demand.get(demand_title_field) or "N/A"
		
		country_field = demand_meta.get_field("country_of_deployment").fieldname if demand_meta.get_field("country_of_deployment") else "country_of_deployment"
		country_value = demand.get(country_field) or "N/A"
		
		demand_reference_no_field = demand_meta.get_field("demand_reference_no").fieldname if demand_meta.get_field("demand_reference_no") else "demand_reference_no"
		demand_reference_no_value = demand.get(demand_reference_no_field) or demand.name
		
		# Get Demand Position details from child table
		demand_position_details = None
		if self.demand_position and hasattr(demand, 'positions') and demand.positions:
			for position in demand.positions:
				if position.job_title == self.demand_position:
					demand_position_details = position
					break
		
		# Build content lines
		info_lines = []
		info_lines.append("=" * 80)
		info_lines.append("JOB OPENING DETAILS")
		info_lines.append("=" * 80)
		info_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
		info_lines.append("")
		
		# ============================================
		# BASIC INFORMATION
		# ============================================
		info_lines.append("BASIC INFORMATION")
		info_lines.append("-" * 80)
		info_lines.append(f"Job Opening ID: {self.name}")
		info_lines.append(f"Job Title: {job_title_value}")
		info_lines.append(f"Status: {self.get('status') or 'N/A'}")
		
		# Get designation if exists
		if hasattr(self, 'designation') and self.get("designation"):
			info_lines.append(f"Designation: {self.designation}")
		
		# Get department if exists
		if hasattr(self, 'department') and self.get("department"):
			info_lines.append(f"Department: {self.department}")
		
		# Get company if exists
		if hasattr(self, 'company') and self.get("company"):
			info_lines.append(f"Company: {self.company}")
		
		info_lines.append("")
		
		# ============================================
		# DEMAND INFORMATION
		# ============================================
		info_lines.append("DEMAND INFORMATION")
		info_lines.append("-" * 80)
		info_lines.append(f"Demand Name: {demand_title_value}")
		info_lines.append(f"Demand Reference No: {demand_reference_no_value}")
		info_lines.append(f"Linked Demand: {self.linked_demand}")
		
		if self.demand_position:
			info_lines.append(f"Demand Position: {self.demand_position}")
		
		# Get demand status if exists
		if hasattr(demand, 'demand_status') and demand.get("demand_status"):
			info_lines.append(f"Demand Status: {demand.demand_status}")
		
		# Get demand received date if exists
		if hasattr(demand, 'demand_received_date') and demand.get("demand_received_date"):
			received_date = demand.demand_received_date
			if hasattr(received_date, 'strftime'):
				info_lines.append(f"Demand Received Date: {received_date.strftime('%Y-%m-%d')}")
			else:
				info_lines.append(f"Demand Received Date: {str(received_date)}")
		
		info_lines.append("")
		
		# ============================================
		# DEMAND POSITION DETAILS (from child table)
		# ============================================
		if demand_position_details:
			info_lines.append("DEMAND POSITION DETAILS")
			info_lines.append("-" * 80)
			
			if hasattr(demand_position_details, 'job_category') and demand_position_details.job_category:
				info_lines.append(f"Job Category: {demand_position_details.job_category}")
			
			if hasattr(demand_position_details, 'quantity') and demand_position_details.quantity:
				info_lines.append(f"Quantity: {demand_position_details.quantity}")
			
			if hasattr(demand_position_details, 'experience_required') and demand_position_details.experience_required:
				info_lines.append(f"Position Experience Required: {demand_position_details.experience_required}")
			
			if hasattr(demand_position_details, 'education_required') and demand_position_details.education_required:
				info_lines.append(f"Position Education Required: {demand_position_details.education_required}")
			
			if hasattr(demand_position_details, 'basic_sallary') and demand_position_details.basic_sallary:
				info_lines.append(f"Position Basic Salary: {demand_position_details.basic_sallary}")
			
			if hasattr(demand_position_details, 'remarks') and demand_position_details.remarks:
				info_lines.append(f"Position Remarks: {demand_position_details.remarks}")
			
			info_lines.append("")
		
		# ============================================
		# DATES
		# ============================================
		info_lines.append("DATES")
		info_lines.append("-" * 80)
		
		if hasattr(self, 'posted_on') and self.get("posted_on"):
			posted_on_value = self.posted_on
			if hasattr(posted_on_value, 'strftime'):
				info_lines.append(f"Posted On: {posted_on_value.strftime('%Y-%m-%d %H:%M:%S')}")
			else:
				info_lines.append(f"Posted On: {str(posted_on_value)}")
		else:
			info_lines.append("Posted On: N/A")
		
		if hasattr(self, 'closes_on') and self.get("closes_on"):
			closes_on_value = self.closes_on
			if hasattr(closes_on_value, 'strftime'):
				info_lines.append(f"Closes On: {closes_on_value.strftime('%Y-%m-%d')}")
			else:
				info_lines.append(f"Closes On: {str(closes_on_value)}")
		else:
			info_lines.append("Closes On: N/A")
		
		if hasattr(self, 'closed_on') and self.get("closed_on"):
			closed_on_value = self.closed_on
			if hasattr(closed_on_value, 'strftime'):
				info_lines.append(f"Closed On: {closed_on_value.strftime('%Y-%m-%d')}")
		
		info_lines.append("")
		
		# ============================================
		# EMPLOYER INFORMATION
		# ============================================
		info_lines.append("EMPLOYER INFORMATION")
		info_lines.append("-" * 80)
		info_lines.append(f"Employer: {employer_name_value}")
		
		# Get employer code if exists
		if hasattr(employer, 'employer_code') and employer.get("employer_code"):
			info_lines.append(f"Employer Code: {employer.employer_code}")
		
		# Get company registration number if exists
		if hasattr(employer, 'company_reg_no') and employer.get("company_reg_no"):
			info_lines.append(f"Company Registration No: {employer.company_reg_no}")
		
		info_lines.append(f"Country of Deployment: {country_value}")
		
		# Get employer city if exists
		if hasattr(employer, 'city') and employer.get("city"):
			info_lines.append(f"City: {employer.city}")
		
		info_lines.append("")
		
		# ============================================
		# REQUIREMENTS
		# ============================================
		info_lines.append("REQUIREMENTS")
		info_lines.append("-" * 80)
		
		# Age requirements
		if hasattr(self, 'age_min') or frappe.db.has_column("Job Opening", "age_min"):
			age_min = self.get("age_min")
			if age_min:
				info_lines.append(f"Age Min: {age_min}")
		
		if hasattr(self, 'age_max') or frappe.db.has_column("Job Opening", "age_max"):
			age_max = self.get("age_max")
			if age_max:
				info_lines.append(f"Age Max: {age_max}")
		
		# Experience and Education
		if hasattr(self, 'experience_required') or frappe.db.has_column("Job Opening", "experience_required"):
			experience = self.get("experience_required")
			if experience:
				info_lines.append(f"Experience Required: {experience}")
		
		if hasattr(self, 'education_required') or frappe.db.has_column("Job Opening", "education_required"):
			education = self.get("education_required")
			if education:
				info_lines.append(f"Education Required: {education}")
		
		info_lines.append("")
		
		# ============================================
		# SALARY INFORMATION
		# ============================================
		info_lines.append("SALARY INFORMATION")
		info_lines.append("-" * 80)
		
		if hasattr(self, 'currency') and self.get("currency"):
			info_lines.append(f"Currency: {self.currency}")
		
		if hasattr(self, 'lower_range') and self.get("lower_range"):
			info_lines.append(f"Lower Range: {self.lower_range}")
		
		if hasattr(self, 'upper_range') and self.get("upper_range"):
			info_lines.append(f"Upper Range: {self.upper_range}")
		
		if hasattr(self, 'salary_per') and self.get("salary_per"):
			info_lines.append(f"Salary Paid Per: {self.salary_per}")
		
		info_lines.append("")
		
		# ============================================
		# INTERVIEW REQUIREMENTS
		# ============================================
		info_lines.append("INTERVIEW REQUIREMENTS")
		info_lines.append("-" * 80)
		
		if hasattr(self, 'internal_hr_required') or frappe.db.has_column("Job Opening", "internal_hr_required"):
			internal_hr = "Yes" if self.get("internal_hr_required") else "No"
			info_lines.append(f"Internal HR Required: {internal_hr}")
		
		if hasattr(self, 'technical_interview_required') or frappe.db.has_column("Job Opening", "technical_interview_required"):
			technical = "Yes" if self.get("technical_interview_required") else "No"
			info_lines.append(f"Technical Interview Required: {technical}")
		
		if hasattr(self, 'trade_test_required') or frappe.db.has_column("Job Opening", "trade_test_required"):
			trade_test = "Yes" if self.get("trade_test_required") else "No"
			info_lines.append(f"Trade Test Required: {trade_test}")
		
		info_lines.append("")
		
		# ============================================
		# ADDITIONAL INFORMATION
		# ============================================
		info_lines.append("ADDITIONAL INFORMATION")
		info_lines.append("-" * 80)
		
		# Get planned vacancies if exists
		if hasattr(self, 'planned_vacancies') and self.get("planned_vacancies"):
			info_lines.append(f"Planned Vacancies: {self.planned_vacancies}")
		
		# Get vacancies if exists
		if hasattr(self, 'vacancies') and self.get("vacancies"):
			info_lines.append(f"Vacancies: {self.vacancies}")
		
		# Get employment type if exists
		if hasattr(self, 'employment_type') and self.get("employment_type"):
			info_lines.append(f"Employment Type: {self.employment_type}")
		
		# Get location if exists
		if hasattr(self, 'location') and self.get("location"):
			info_lines.append(f"Location: {self.location}")
		
		# Get description if exists
		if hasattr(self, 'description') and self.get("description"):
			info_lines.append("")
			info_lines.append("Description:")
			info_lines.append("-" * 80)
			# Clean HTML tags from description if it's HTML
			description = self.description
			if description:
				# Remove HTML tags for text file
				import re
				description = re.sub(r'<[^>]+>', '', str(description))
				info_lines.append(description)
		
		info_lines.append("")
		
		# ============================================
		# FOOTER
		# ============================================
		info_lines.append("=" * 80)
		info_lines.append(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
		info_lines.append("=" * 80)
		
		return "\n".join(info_lines)
	
	def update_job_opening_txt_file(self):
		"""
		Function: update_job_opening_txt_file
		Purpose: Update job_opening_details.txt when Job Opening is updated
		"""
		if not self.linked_demand:
			return
		
		try:
			job_opening_folder = self.get_job_opening_drive_folder()
			if not job_opening_folder:
				# Folder doesn't exist, create structure
				self.create_job_opening_drive_structure()
				return
			
			# Get Demand and Employer
			demand = frappe.get_doc("Demand", self.linked_demand)
			if not demand.employer:
				return
			
			employer = frappe.get_doc("Employer", demand.employer)
			team = employer.get_drive_team()
			if not team:
				return
			
			# Regenerate text file
			self.generate_job_opening_txt_file(job_opening_folder, team, employer, demand)
			
		except Exception as e:
			frappe.log_error(
				f"Error updating job_opening_details.txt for Job Opening {self.name}: {str(e)}\n{frappe.get_traceback()}",
				"Job Opening Text File Update Error"
			)
	
	def has_job_opening_info_changed(self):
		"""
		Function: has_job_opening_info_changed
		Purpose: Check if any Job Opening information fields have changed
		Returns: True if any relevant field changed, False otherwise
		"""
		# List of fields that should trigger text file update
		info_fields = [
			"job_title", "demand_position", "status", "age_min", "age_max",
			"experience_required", "education_required", "internal_hr_required",
			"technical_interview_required", "trade_test_required", "posted_on"
		]
		
		# Check if any of these fields changed
		for field in info_fields:
			if self.has_value_changed(field):
				return True
		
		return False
	
	def create_drive_text_file(self, file_name, parent_folder, content, team):
		"""
		Function: create_drive_text_file
		Purpose: Create a text file in Drive with specified content
		Parameters:
			- file_name: Name of the file to create
			- parent_folder: Parent Drive File document name
			- content: Text content for the file
			- team: Drive team name
		"""
		try:
			frappe.msgprint(f"[DEBUG] create_drive_text_file STARTED: file={file_name}, folder={parent_folder}", indicator="blue", alert=True)
			from drive.utils import create_drive_file
			from drive.utils.files import FileManager
			from drive.utils import get_home_folder
			from pathlib import Path
			
			# Get home folder
			home_folder = get_home_folder(team)
			if not home_folder:
				frappe.msgprint(f"[DEBUG] FAILED: Home folder not found for team {team}", indicator="red", alert=True)
				frappe.log_error(
					f"Home folder not found for team {team} for Job Opening {self.name}",
					"Job Opening Text File Creation Error"
				)
				return
			
			frappe.msgprint(f"[DEBUG] Home folder found: {home_folder}", indicator="blue", alert=True)
			
			# Get parent folder document
			try:
				parent_doc = frappe.get_doc("Drive File", parent_folder)
				frappe.msgprint(f"[DEBUG] Parent folder loaded: {parent_doc.name}, path={parent_doc.path}", indicator="blue", alert=True)
			except frappe.DoesNotExistError:
				frappe.msgprint(f"[DEBUG] FAILED: Parent folder {parent_folder} does not exist", indicator="red", alert=True)
				frappe.log_error(
					f"Parent folder {parent_folder} does not exist for Job Opening {self.name}",
					"Job Opening Text File Creation Error"
				)
				return
			
			# Validate content
			if not content:
				frappe.msgprint(f"[DEBUG] FAILED: Content is empty", indicator="red", alert=True)
				frappe.log_error(
					f"Content is empty for file {file_name} for Job Opening {self.name}",
					"Job Opening Text File Creation Error"
				)
				return
			
			frappe.msgprint(f"[DEBUG] Content validated, length={len(content)} chars", indicator="blue", alert=True)
			
			# Create file path using FileManager (exact same as Employer implementation)
			frappe.msgprint(f"[DEBUG] Creating file using FileManager...", indicator="blue", alert=True)
			manager = FileManager()
			file_path = manager.create_file(
				frappe._dict({
					"title": file_name,
					"team": team,
					"parent_path": Path(parent_doc.path or ""),
				}),
				home_folder,
				content.encode('utf-8'),
			)
			
			frappe.msgprint(f"[DEBUG] FileManager.create_file returned: {file_path}", indicator="blue", alert=True)
			
			# Create Drive File document
			frappe.msgprint(f"[DEBUG] Creating Drive File document...", indicator="blue", alert=True)
			drive_file = create_drive_file(
				team=team,
				title=file_name,
				parent=parent_folder,
				mime_type="text/plain",
				entity_path=lambda _: file_path,
				is_group=False,
			)
			
			frappe.msgprint(f"[DEBUG] create_drive_file returned: name={getattr(drive_file, 'name', 'NO NAME')}", indicator="blue", alert=True)
			
			# Commit to ensure file is saved to database
			frappe.db.commit()
			frappe.msgprint(f"[DEBUG] Database committed", indicator="blue", alert=True)
			
			# Verify file was created
			if drive_file and hasattr(drive_file, 'name') and drive_file.name:
				# Verify file exists in database after commit
				created_file = frappe.db.get_value(
					"Drive File",
					{"name": drive_file.name, "is_active": 1, "is_group": 0},
					"name"
				)
				if created_file:
					frappe.msgprint(f"[DEBUG] SUCCESS: File verified in DB: {created_file}", indicator="green", alert=True)
					frappe.log_error(
						f"Successfully created job_opening_details.txt (Drive File: {drive_file.name}) for Job Opening {self.name} in folder {parent_folder}",
						"Job Opening Text File Creation Success",
						is_error=False
					)
				else:
					frappe.msgprint(f"[DEBUG] WARNING: File created but NOT found in DB: {drive_file.name}", indicator="orange", alert=True)
					frappe.log_error(
						f"Drive file document created ({drive_file.name}) but not found in database after commit for Job Opening {self.name}",
						"Job Opening Text File Creation Warning"
					)
			else:
				frappe.log_error(
					f"create_drive_file returned None or invalid object for Job Opening {self.name}",
					"Job Opening Text File Creation Error"
				)
			
		except Exception as e:
			error_msg = f"Error creating Drive text file {file_name} for Job Opening {self.name} in folder {parent_folder}: {str(e)}\n{frappe.get_traceback()}"
			frappe.log_error(
				error_msg,
				"Job Opening Drive Text File Creation Error"
			)
			# Re-raise to ensure caller knows it failed
			raise
	
	def update_drive_file_content(self, drive_file_name, new_content, team):
		"""
		Function: update_drive_file_content
		Purpose: Update the content of an existing Drive file
		Parameters:
			- drive_file_name: Drive File document name
			- new_content: New text content
			- team: Drive team name
		"""
		try:
			from drive.utils.files import FileManager
			from drive.utils import get_home_folder
			from pathlib import Path
			
			# Get Drive File document
			drive_file_doc = frappe.get_doc("Drive File", drive_file_name)
			
			# Get home folder
			home_folder = get_home_folder(team)
			if not home_folder:
				return
			
			# Update file content using FileManager
			manager = FileManager()
			file_path = manager.create_file(
				frappe._dict({
					"title": drive_file_doc.title,
					"team": team,
					"parent_path": Path(drive_file_doc.path.parent if drive_file_doc.path else ""),
				}),
				home_folder,
				new_content.encode('utf-8'),
			)
			
			# Update Drive File document path
			drive_file_doc.path = file_path
			drive_file_doc.save(ignore_permissions=True)
			frappe.db.commit()
			
		except Exception as e:
			frappe.log_error(
				f"Error updating Drive file content {drive_file_name} for Job Opening {self.name}: {str(e)}\n{frappe.get_traceback()}",
				"Job Opening Drive File Update Error"
			)
			raise
	
	@frappe.whitelist()
	def create_drive_folder_and_file(self):
		"""
		Function: create_drive_folder_and_file
		Purpose: Whitelisted method to manually create Drive folder and text file for Job Opening
		Returns: Dictionary with success status and message
		"""
		if not self.linked_demand:
			return {
				"success": False,
				"message": _("Linked Demand is required to create Drive folder")
			}
		
		try:
			result = self.create_job_opening_drive_structure()
			if result:
				# Verify file was created
				job_opening_folder = self.get_job_opening_drive_folder()
				if job_opening_folder:
					# Check if file exists
					file_exists = frappe.db.get_value(
						"Drive File",
						{
							"title": "job_opening_details.txt",
							"parent_entity": job_opening_folder,
							"is_active": 1,
							"is_group": 0
						},
						"name"
					)
					
					if file_exists:
						return {
							"success": True,
							"message": _("Drive folder and job_opening_details.txt created successfully for {0}").format(self.name)
						}
					else:
						# Try to create file again
						try:
							demand = frappe.get_doc("Demand", self.linked_demand)
							employer = frappe.get_doc("Employer", demand.employer)
							team = employer.get_drive_team()
							if team:
								self.generate_job_opening_txt_file(job_opening_folder, team, employer, demand)
								return {
									"success": True,
									"message": _("Drive folder created. Text file creation attempted. Please check Drive.")
								}
						except Exception as file_error:
							return {
								"success": False,
								"message": _("Folder created but file creation failed: {0}").format(str(file_error))
							}
				
				return {
					"success": True,
					"message": _("Drive folder created successfully for {0}").format(self.name)
				}
			else:
				return {
					"success": False,
					"message": _("Failed to create Drive folder. Please check Error Log for details.")
				}
		except Exception as e:
			error_msg = str(e)
			frappe.log_error(
				f"Error creating Drive folder for Job Opening {self.name}: {error_msg}\n{frappe.get_traceback()}",
				"Job Opening Drive Folder Creation Error"
			)
			return {
				"success": False,
				"message": _("Error creating Drive folder: {0}").format(error_msg)
			}
	
	@frappe.whitelist()
	def create_text_file_only(self):
		"""
		Function: create_text_file_only
		Purpose: Whitelisted method to create only the text file (if folder exists)
		Returns: Dictionary with success status and message
		"""
		if not self.linked_demand:
			return {
				"success": False,
				"message": _("Linked Demand is required")
			}
		
		try:
			job_opening_folder = self.get_job_opening_drive_folder()
			if not job_opening_folder:
				return {
					"success": False,
					"message": _("Job Opening Drive folder not found. Please create folder first.")
				}
			
			demand = frappe.get_doc("Demand", self.linked_demand)
			if not demand.employer:
				return {
					"success": False,
					"message": _("Demand has no linked Employer")
				}
			
			employer = frappe.get_doc("Employer", demand.employer)
			team = employer.get_drive_team()
			if not team:
				return {
					"success": False,
					"message": _("No Drive team found")
				}
			
			# Generate text file
			self.generate_job_opening_txt_file(job_opening_folder, team, employer, demand)
			
			# Verify file was created
			frappe.db.commit()
			file_exists = frappe.db.get_value(
				"Drive File",
				{
					"title": "job_opening_details.txt",
					"parent_entity": job_opening_folder,
					"is_active": 1,
					"is_group": 0
				},
				"name"
			)
			
			if file_exists:
				return {
					"success": True,
					"message": _("Text file created successfully")
				}
			else:
				return {
					"success": False,
					"message": _("Text file creation attempted but file not found. Check Error Log.")
				}
			
		except Exception as e:
			error_msg = str(e)
			frappe.log_error(
				f"Error creating text file for Job Opening {self.name}: {error_msg}\n{frappe.get_traceback()}",
				"Job Opening Text File Creation Error"
			)
			return {
				"success": False,
				"message": _("Error: {0}").format(error_msg)
			}
