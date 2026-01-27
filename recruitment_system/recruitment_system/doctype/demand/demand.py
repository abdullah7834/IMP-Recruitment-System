# Copyright (c) 2026, abdullahjavaid198@gmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class Demand(Document):
	def after_insert(self):
		"""
		Function: after_insert
		Purpose: Create Drive folder structure when Demand is first created
		Operation: Calls create_demand_drive_structure() to set up all folders
		Trigger: Called automatically after document is inserted into database
		"""
		# Create folder structure (non-blocking - errors are logged but don't prevent Demand creation)
		self.create_demand_drive_structure()
	
	def on_update(self):
		"""
		Function: on_update
		Purpose: Handle folder rename when Demand.name changes, process document files
		Operation:
			- Checks if Demand.name changed (manual rename)
			- Renames folder if name changed (preserves all subfolders and files)
			- Ensures folder structure exists (creates if missing)
			- Processes any document files from attach fields
		Trigger: Called automatically when document is updated
		"""
		# Check if Demand.name changed (affects folder name)
		# Note: In Frappe, when a document is renamed, the name field changes
		# We need to get the old name from the database or doc_before_save
		old_name = None
		if self.has_value_changed("name"):
			# Try to get old name from doc_before_save
			doc_before_save = self.get_doc_before_save()
			if doc_before_save:
				old_name = doc_before_save.name
			else:
				# Fallback: check if there's a folder with a different name
				# This handles the case where name changed but we don't have old name
				pass
		
		# If name changed, rename the folder
		if old_name and old_name != self.name and self.name and self.employer:
			self.rename_demand_folder_with_old_name(old_name)
		
		# Ensure folder structure exists (in case it wasn't created on insert) - idempotent
		if self.name and self.employer:
			self.create_demand_drive_structure()
		
		# Process files from attach fields (runs after files are attached)
		if self.name and self.employer:
			self.process_demand_document_files()
	
	def on_trash(self):
		"""
		Function: on_trash
		Purpose: Delete Demand Drive folder when Demand is deleted
		Operation:
			- Checks for force_delete_drive_folder flag
			- If TRUE: deletes /Demands/{Demand ID}/ and all contents
			- If FALSE: blocks deletion with a clear error message
		Trigger: Called automatically before document is deleted from database
		"""
		# Check for force_delete_drive_folder flag from multiple sources
		force_delete = False
		field_exists_in_db = False
		
		# First, check if field exists in database (for migration compatibility)
		try:
			meta = frappe.get_meta("Demand")
			if meta.has_field("force_delete_drive_folder"):
				field_exists_in_db = frappe.db.has_column("Demand", "force_delete_drive_folder")
		except Exception:
			pass
		
		# If field doesn't exist in DB yet (migration not run), allow deletion for backward compatibility
		if not field_exists_in_db:
			# Field not migrated yet, allow deletion (backward compatibility)
			force_delete = True
		else:
			# Field exists, check all sources
			# Check frappe.flags first (for programmatic deletions with explicit flag)
			if frappe.flags.get("force_delete_drive_folder") is not None:
				force_delete = bool(frappe.flags.get("force_delete_drive_folder"))
			
			# Check frappe.form_dict (for API deletions)
			if not force_delete and frappe.form_dict.get("force_delete_drive_folder") is not None:
				force_delete = bool(frappe.form_dict.get("force_delete_drive_folder"))
			
			# Check document field (if loaded in form)
			if not force_delete and hasattr(self, 'force_delete_drive_folder'):
				force_delete = bool(self.force_delete_drive_folder)
			
			# Check database value (for list view deletions)
			if not force_delete:
				try:
					db_value = frappe.db.get_value("Demand", self.name, "force_delete_drive_folder")
					if db_value is not None:
						force_delete = bool(db_value)
				except Exception as e:
					# Error reading from database, log and block deletion for safety
					frappe.log_error(
						f"Error reading force_delete_drive_folder field for Demand {self.name}: {str(e)}",
						"Demand Delete Check Error"
					)
					force_delete = False
		
		if not force_delete:
			frappe.throw(
				_("Cannot delete Demand. Please open the Demand record, check the 'Force Delete Drive Folder' checkbox, save the record, then try deleting again."),
				title=_("Deletion Blocked")
			)
		
		# Delete folder structure
		# Use try-except to ensure Demand deletion succeeds even if Drive deletion fails
		try:
			self.delete_demand_folder()
		except Exception as e:
			# Log error but don't prevent Demand deletion
			frappe.log_error(
				f"Error deleting Drive folders for Demand {self.name} during deletion: {str(e)}\n{frappe.get_traceback()}",
				"Demand Drive Folder Deletion Error"
			)
	
	def create_demand_drive_structure(self):
		"""
		Function: create_demand_drive_structure
		Purpose: Create the complete Drive folder structure for a Demand using Frappe Drive
		Operation:
			1. Get linked Employer
			2. Locate Employer.drive_root_folder or /Employers/{Employer Name}/
			3. Ensure /Demands/ exists
			4. Create /Demands/{Demand ID}/
			5. Create all required subfolders: Demand_Letter, POA, Attestation, Approvals, Other_Documents
			6. Save Demand.drive_folder_path and drive_folder_url
		Returns: True if successful, False otherwise
		"""
		if not self.name or not self.employer:
			return False
		
		try:
			# Check if Drive app is installed
			if not frappe.db.exists("DocType", "Drive File"):
				frappe.log_error(
					"Drive app is not installed. Please install the Drive app to enable folder creation.",
					"Demand Drive Folder Creation Error"
				)
				return False
			
			# Get linked Employer
			try:
				employer = frappe.get_doc("Employer", self.employer)
			except frappe.DoesNotExistError:
				frappe.log_error(
					f"Employer {self.employer} not found for Demand {self.name}",
					"Demand Drive Folder Creation Error"
				)
				return False
			
			# Get Employer's Drive folder
			employer_folder = employer.get_employer_drive_folder()
			if not employer_folder:
				# Try to create Employer folder structure first
				employer.create_employer_drive_structure()
				employer_folder = employer.get_employer_drive_folder()
				if not employer_folder:
					frappe.log_error(
						f"Cannot find or create Drive folder for Employer {self.employer}",
						"Demand Drive Folder Creation Error"
					)
					return False
			
			# Get team
			team = employer.get_drive_team()
			if not team:
				frappe.log_error(
					f"No Drive team found for Demand {self.name}",
					"Demand Drive Folder Creation Error"
				)
				return False
			
			# Step 1: Ensure /Demands/ folder exists under Employer folder
			demands_folder = employer.get_or_create_drive_folder("Demands", employer_folder, team)
			if not demands_folder:
				frappe.log_error(
					f"Failed to create/get 'Demands' folder in Employer folder '{employer_folder}' for team '{team}'",
					"Demand Drive Folder Creation Error"
				)
				return False
			
			# Step 2: Build folder name using format: "{demand_title}-{demand_reference_no}"
			# Get field names from meta to avoid hardcoding
			meta = frappe.get_meta("Demand")
			demand_title_field = meta.get_field("demand_title").fieldname if meta.get_field("demand_title") else "demand_title"
			demand_reference_no_field = meta.get_field("demand_reference_no").fieldname if meta.get_field("demand_reference_no") else "demand_reference_no"
			
			demand_title_value = self.get(demand_title_field) or ""
			demand_reference_no_value = self.get(demand_reference_no_field) or self.name  # Fallback to name if field not set
			
			if not demand_title_value or not demand_reference_no_value:
				frappe.log_error(
					f"Missing required fields for folder creation: demand_title={demand_title_value}, demand_reference_no={demand_reference_no_value}",
					"Demand Drive Folder Creation Error"
				)
				return False
			
			# Format: "{demand_title}-{demand_reference_no}"
			demand_folder_name = f"{demand_title_value}-{demand_reference_no_value}"
			# Sanitize folder name (use Employer's sanitize method)
			demand_folder_name = employer.sanitize_folder_name(demand_folder_name)
			
			# Ensure folder name doesn't exceed limit (140 chars)
			if len(demand_folder_name) > 140:
				demand_folder_name = demand_folder_name[:137] + "..."
			
			# Check if Demand folder already exists (reuse existing folder)
			existing_demand_folder = self.get_drive_folder_by_title(demand_folder_name, demands_folder, team)
			
			if existing_demand_folder:
				# Folder already exists, reuse it
				demand_folder = existing_demand_folder
			else:
				# Step 3: Create /Demands/{Demand Title}-{Demand Reference No}/ folder
				demand_folder = employer.get_or_create_drive_folder(demand_folder_name, demands_folder, team)
				if not demand_folder:
					frappe.log_error(
						f"Failed to create Demand folder '{demand_folder_name}' in 'Demands' folder for team '{team}'",
						"Demand Drive Folder Creation Error"
					)
					return False
			
			# Step 4: Create all required subfolders
			subfolders = ["Demand_Letter", "POA", "Attestation", "Approvals", "Other_Documents", "Job_Openings"]
			for subfolder_name in subfolders:
				self.ensure_subfolder(subfolder_name, demand_folder, team)
			
			# Step 5: Save folder references (if fields exist)
			# Use db_set to avoid recursion during insert
			if hasattr(self, 'drive_folder_path') or frappe.db.has_column("Demand", "drive_folder_path"):
				try:
					# Get folder path for storage using new format
					# Get employer folder name format
					employer_meta = frappe.get_meta("Employer")
					employer_name_field = employer_meta.get_field("employer_name").fieldname if employer_meta.get_field("employer_name") else "employer_name"
					company_reg_no_field = employer_meta.get_field("company_reg_no").fieldname if employer_meta.get_field("company_reg_no") else "company_reg_no"
					
					employer_name_value = employer.get(employer_name_field) or ""
					company_reg_no_value = employer.get(company_reg_no_field) or ""
					
					employer_folder_name = f"{employer_name_value}-{company_reg_no_value}" if employer_name_value and company_reg_no_value else employer.name
					
					# Get folder path for storage
					folder_path = f"/Employers/{employer_folder_name}/Demands/{demand_folder_name}"
					self.db_set("drive_folder_path", folder_path, update_modified=False)
				except Exception:
					pass
			
			if hasattr(self, 'drive_folder_url') or frappe.db.has_column("Demand", "drive_folder_url"):
				try:
					# Generate Drive folder URL (optional)
					folder_url = f"/app/drive/{demand_folder}"
					self.db_set("drive_folder_url", folder_url, update_modified=False)
				except Exception:
					pass
			
			return True
			
		except Exception as e:
			# Log detailed error information
			error_details = {
				"demand_id": self.name,
				"employer": self.employer,
				"user": frappe.session.user,
				"error": str(e),
				"traceback": frappe.get_traceback()
			}
			frappe.log_error(
				f"Error creating Drive folders for Demand {self.name} (Employer: {self.employer}): {str(e)}\n{frappe.get_traceback()}\nDetails: {error_details}",
				"Demand Drive Folder Creation Error"
			)
			# Don't throw error - allow Demand creation to succeed even if folder creation fails
			return False
	
	def ensure_subfolder(self, subfolder_name, parent_folder, team):
		"""
		Function: ensure_subfolder
		Purpose: Ensure a subfolder exists, create if it doesn't
		Parameters:
			- subfolder_name: Name of the subfolder
			- parent_folder: Parent Drive File document name
			- team: Drive team name
		Returns: Drive File document name (string) or None
		"""
		try:
			# Get Employer to use its helper methods
			if not self.employer:
				return None
			
			employer = frappe.get_doc("Employer", self.employer)
			return employer.get_or_create_drive_folder(subfolder_name, parent_folder, team)
		except Exception as e:
			frappe.log_error(
				f"Error ensuring subfolder '{subfolder_name}' in parent '{parent_folder}': {str(e)}",
				"Demand Subfolder Creation Error"
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
	
	def get_demand_drive_folder(self):
		"""
		Function: get_demand_drive_folder
		Purpose: Get the main Drive folder for this Demand
		Operation:
			- Gets Employer folder
			- Finds /Demands/{Demand ID}/ folder
		Returns: Drive File document name (string) or None
		"""
		if not self.name or not self.employer:
			return None
		
		try:
			employer = frappe.get_doc("Employer", self.employer)
			employer_folder = employer.get_employer_drive_folder()
			if not employer_folder:
				return None
			
			team = employer.get_drive_team()
			if not team:
				return None
			
			# Get Demands folder
			demands_folder = self.get_drive_folder_by_title("Demands", employer_folder, team)
			if not demands_folder:
				return None
			
			# Find Demand folder by demand_reference_no (search in folder title)
			# Get field names from meta to avoid hardcoding
			meta = frappe.get_meta("Demand")
			demand_title_field = meta.get_field("demand_title").fieldname if meta.get_field("demand_title") else "demand_title"
			demand_reference_no_field = meta.get_field("demand_reference_no").fieldname if meta.get_field("demand_reference_no") else "demand_reference_no"
			
			demand_title_value = self.get(demand_title_field) or ""
			demand_reference_no_value = self.get(demand_reference_no_field) or self.name
			
			if not demand_reference_no_value:
				return None
			
			# Try to find by full format: "{demand_title}-{demand_reference_no}"
			if demand_title_value:
				folder_name = f"{demand_title_value}-{demand_reference_no_value}"
				folder_name = employer.sanitize_folder_name(folder_name)
				found_folder = self.get_drive_folder_by_title(folder_name, demands_folder, team)
				if found_folder:
					return found_folder
			
			# Fallback: search by demand_reference_no in folder title (more reliable since it's the ID)
			# Search all folders in Demands folder and find one that ends with demand_reference_no
			all_folders = frappe.get_all(
				"Drive File",
				filters={
					"parent_entity": demands_folder,
					"is_group": 1,
					"is_active": 1,
					"team": team
				},
				fields=["name", "title"]
			)
			
			for folder in all_folders:
				# Check if folder title ends with demand_reference_no
				if folder.get("title", "").endswith(f"-{demand_reference_no_value}") or folder.get("title", "") == demand_reference_no_value:
					return folder.get("name")
			
			return None
			
		except Exception as e:
			frappe.log_error(
				f"Error getting Drive folder for Demand {self.name}: {str(e)}",
				"Demand Drive Folder Lookup Error"
			)
			return None
	
	def process_demand_document_files(self):
		"""
		Function: process_demand_document_files
		Purpose: Process files from Demand attach fields and move them to correct Drive subfolders
		Operation:
			- Ensures folder structure exists (creates if missing)
			- Gets all attach field values
			- Handles file replacement (deletes old files when replaced)
			- Moves each file to the correct subfolder based on field mapping
		"""
		if not self.name or not self.employer:
			return
		
		# Ensure folder structure exists
		if not self.create_demand_drive_structure():
			return
		
		demand_folder = self.get_demand_drive_folder()
		if not demand_folder:
			return
		
		try:
			employer = frappe.get_doc("Employer", self.employer)
			team = employer.get_drive_team()
			if not team:
				return
			
			# Map fields to subfolders
			field_mapping = {
				"demand_letter": "Demand_Letter",
				"power_of_attorney_poa": "POA",
				"attested_copy": "Attestation",
			}
			
			# Process each attach field
			for field_name, subfolder_name in field_mapping.items():
				# Check if file was replaced
				if self.has_value_changed(field_name):
					# Get old file URL
					doc_before_save = self.get_doc_before_save()
					old_file_url = doc_before_save.get(field_name) if doc_before_save else None
					
					# Delete old Drive file if it exists
					if old_file_url:
						self.delete_drive_file_by_url(old_file_url, subfolder_name, demand_folder, team)
				
				# Process new file
				file_url = self.get(field_name)
				if file_url:
					self.move_uploaded_file(file_url, subfolder_name, demand_folder, team)
			
			# Handle Bureau/Embassy approvals - check if there are any approval-related files
			# This could be in a separate field or we can check for files with specific naming
			# For now, we'll handle it if there's a field for it in the future
			
		except Exception as e:
			frappe.log_error(
				f"Error processing document files for Demand {self.name}: {str(e)}\n{frappe.get_traceback()}",
				"Demand Document File Processing Error"
			)
	
	def move_uploaded_file(self, file_url, subfolder_name, demand_folder, team):
		"""
		Function: move_uploaded_file
		Purpose: Move an uploaded file to the correct Demand subfolder
		Parameters:
			- file_url: File URL from attach field
			- subfolder_name: Target subfolder name (Demand_Letter, POA, Attestation, Approvals, Other_Documents)
			- demand_folder: Demand's main Drive folder name
			- team: Drive team name
		"""
		if not file_url or not subfolder_name or not demand_folder:
			return
		
		try:
			# Find File document
			file_doc = self.find_file_document_by_url(file_url)
			if not file_doc:
				return
			
			# Ensure subfolder exists
			subfolder = self.ensure_subfolder(subfolder_name, demand_folder, team)
			if not subfolder:
				return
			
			# Check if Drive File already exists in the correct location
			existing_drive_file = frappe.db.get_value(
				"Drive File",
				{
					"title": file_doc.file_name,
					"parent_entity": subfolder,
					"team": team,
					"is_active": 1
				},
				"name"
			)
			
			if existing_drive_file:
				# Already in correct location
				return
			
			# Check if Drive File exists elsewhere (need to move it)
			existing_drive_file_anywhere = frappe.db.get_value(
				"Drive File",
				{
					"title": file_doc.file_name,
					"team": team,
					"is_active": 1,
					"is_group": 0
				},
				"name"
			)
			
			if existing_drive_file_anywhere:
				# Move existing Drive File to correct folder
				try:
					drive_file_doc = frappe.get_doc("Drive File", existing_drive_file_anywhere)
					if drive_file_doc.parent_entity != subfolder:
						drive_file_doc.move(new_parent=subfolder)
				except Exception as e:
					frappe.log_error(
						f"Error moving Drive File {existing_drive_file_anywhere}: {str(e)}",
						"Drive File Move Error"
					)
				return
			
			# Create new Drive File entry from File document
			self.create_drive_file_from_file_doc(file_doc, subfolder, team)
			
		except Exception as e:
			frappe.log_error(
				f"Error moving uploaded file {file_url} to subfolder {subfolder_name}: {str(e)}\n{frappe.get_traceback()}",
				"Demand File Move Error"
			)
	
	def find_file_document_by_url(self, file_url):
		"""
		Function: find_file_document_by_url
		Purpose: Find File document by file URL
		Parameters:
			- file_url: File URL string
		Returns: File document or None
		"""
		if not file_url:
			return None
		
		# Method 1: Lookup by file_url (exact match)
		file_name = frappe.db.get_value("File", {"file_url": file_url}, "name")
		
		# Method 2: Extract filename from URL and lookup
		if not file_name:
			file_url_clean = file_url
			if "/files/" in file_url_clean:
				file_url_clean = file_url_clean.split("/files/")[-1]
			if "/private/files/" in file_url_clean:
				file_url_clean = file_url_clean.split("/private/files/")[-1]
			file_name_from_url = file_url_clean.split("/")[-1].split("?")[0]
			file_name = frappe.db.get_value("File", {"file_name": file_name_from_url}, "name")
		
		# Method 3: Lookup by attached_to (files attached to this Demand)
		if not file_name and self.name:
			file_name = frappe.db.get_value(
				"File",
				{
					"attached_to_name": self.name,
					"attached_to_doctype": "Demand",
					"file_url": file_url
				},
				"name",
				order_by="creation desc"
			)
		
		if file_name:
			try:
				return frappe.get_doc("File", file_name)
			except frappe.DoesNotExistError:
				return None
		
		return None
	
	def create_drive_file_from_file_doc(self, file_doc, parent_folder, team):
		"""
		Function: create_drive_file_from_file_doc
		Purpose: Create a Drive File entry from a Frappe File document
		Parameters:
			- file_doc: Frappe File document
			- parent_folder: Parent Drive File document name (subfolder)
			- team: Drive team name
		"""
		try:
			from pathlib import Path
			from drive.utils import create_drive_file, get_home_folder
			from drive.utils.files import FileManager
			import mimetypes
			
			# Get file path using File document's method
			if hasattr(file_doc, 'get_full_path'):
				file_path = Path(file_doc.get_full_path())
			else:
				# Construct path manually
				if file_doc.is_private:
					file_path = Path(frappe.get_site_path("private", "files", file_doc.file_name))
				else:
					file_path = Path(frappe.get_site_path("public", "files", file_doc.file_name))
			
			# Check if file exists
			if not file_path.exists():
				frappe.log_error(
					f"File not found at path: {file_path} for File document {file_doc.name}",
					"Drive File Creation Error"
				)
				return
			
			# Get file size
			file_size = file_path.stat().st_size if file_path.exists() else (file_doc.file_size or 0)
			
			# Get mime type
			mime_type, _ = mimetypes.guess_type(file_doc.file_name)
			if not mime_type:
				mime_type = getattr(file_doc, 'content_type', None) or "application/octet-stream"
			
			# Get home folder for path calculation
			home_folder = get_home_folder(team)
			if not home_folder:
				frappe.log_error(
					f"Home folder not found for team {team}",
					"Drive File Creation Error"
				)
				return
			
			# Create Drive File document first
			manager = FileManager()
			drive_file = create_drive_file(
				team=team,
				title=file_doc.file_name,
				parent=parent_folder,
				mime_type=mime_type,
				entity_path=lambda entity: manager.get_disk_path(entity, home_folder, embed=0),
				file_size=file_size,
				is_group=False,
			)
			
			# Upload file content to Drive storage using FileManager.upload_file
			if file_path.exists() and drive_file:
				manager.upload_file(file_path, drive_file, create_thumbnail=True)
			
		except Exception as e:
			frappe.log_error(
				f"Error creating Drive file for File {file_doc.name}: {str(e)}\n{frappe.get_traceback()}",
				"Drive File Creation Error"
			)
	
	def rename_demand_folder_with_old_name(self, old_name):
		"""
		Function: rename_demand_folder_with_old_name
		Purpose: Rename Demand folder when Demand.name changes (manual rename)
		Operation:
			- Finds existing folder using old name
			- Renames folder to new name: {Demand.name}
			- Preserves all subfolders and files
			- Updates stored folder references
		Parameters:
			- old_name: The old Demand name (before rename)
		"""
		if not self.name or not self.employer or not old_name or old_name == self.name:
			return
		
		try:
			employer = frappe.get_doc("Employer", self.employer)
			team = employer.get_drive_team()
			if not team:
				return
			
			employer_folder = employer.get_employer_drive_folder()
			if not employer_folder:
				return
			
			# Find Demands folder
			demands_folder = self.get_drive_folder_by_title("Demands", employer_folder, team)
			if not demands_folder:
				return
			
			# Find old folder by old_name (which is demand_reference_no)
			# Get field names from meta
			meta = frappe.get_meta("Demand")
			demand_title_field = meta.get_field("demand_title").fieldname if meta.get_field("demand_title") else "demand_title"
			demand_reference_no_field = meta.get_field("demand_reference_no").fieldname if meta.get_field("demand_reference_no") else "demand_reference_no"
			
			# Try to get old demand_title from database
			old_demand_title = frappe.db.get_value("Demand", old_name, demand_title_field) if old_name else None
			
			# Build old folder name
			old_folder_name = None
			if old_demand_title and old_name:
				old_folder_name = f"{old_demand_title}-{old_name}"
				old_folder_name = employer.sanitize_folder_name(old_folder_name)
			
			# Find old folder by name
			old_folder = None
			if old_folder_name:
				old_folder = self.get_drive_folder_by_title(old_folder_name, demands_folder, team)
			
			# If not found, search by old_name (demand_reference_no)
			if not old_folder and old_name:
				all_folders = frappe.get_all(
					"Drive File",
					filters={
						"parent_entity": demands_folder,
						"is_group": 1,
						"is_active": 1,
						"team": team
					},
					fields=["name", "title"]
				)
				for folder in all_folders:
					if folder.get("title", "").endswith(f"-{old_name}") or folder.get("title", "") == old_name:
						old_folder = folder.get("name")
						break
			
			if old_folder:
				# Build new folder name: "{demand_title}-{demand_reference_no}"
				meta = frappe.get_meta("Demand")
				demand_title_field = meta.get_field("demand_title").fieldname if meta.get_field("demand_title") else "demand_title"
				demand_reference_no_field = meta.get_field("demand_reference_no").fieldname if meta.get_field("demand_reference_no") else "demand_reference_no"
				
				demand_title_value = self.get(demand_title_field) or ""
				demand_reference_no_value = self.get(demand_reference_no_field) or self.name
				
				if demand_title_value and demand_reference_no_value:
					new_folder_name = f"{demand_title_value}-{demand_reference_no_value}"
					new_folder_name = employer.sanitize_folder_name(new_folder_name)
					
					# Ensure folder name doesn't exceed limit
					if len(new_folder_name) > 140:
						new_folder_name = new_folder_name[:137] + "..."
					
					# Rename folder
					self.rename_drive_folder(old_folder, new_folder_name, team)
					
					# Update folder references
					if hasattr(self, 'drive_folder_path') or frappe.db.has_column("Demand", "drive_folder_path"):
						try:
							folder_path = f"/Employers/{employer.employer_name}/Demands/{new_folder_name}"
							self.db_set("drive_folder_path", folder_path, update_modified=False)
						except Exception:
							pass
			
		except Exception as e:
			frappe.log_error(
				f"Error renaming Drive folder for Demand from {old_name} to {self.name}: {str(e)}\n{frappe.get_traceback()}",
				"Demand Drive Folder Rename Error"
			)
	
	def rename_drive_folder(self, folder_name, new_title, team):
		"""
		Function: rename_drive_folder
		Purpose: Rename a Drive folder
		Parameters:
			- folder_name: Current Drive File document name
			- new_title: New folder title
			- team: Drive team name
		"""
		try:
			folder_doc = frappe.get_doc("Drive File", folder_name)
			folder_doc.title = new_title
			folder_doc.save(ignore_permissions=True)
		except Exception as e:
			frappe.log_error(
				f"Error renaming Drive folder {folder_name} to {new_title}: {str(e)}\n{frappe.get_traceback()}",
				"Drive Folder Rename Error"
			)
	
	def delete_demand_folder(self):
		"""
		Function: delete_demand_folder
		Purpose: Delete the Demand Drive folder and all its contents
		Operation:
			1. Find the Demand's folder using /Demands/{Demand ID}/
			2. Recursively delete all files and subfolders
			3. Delete the main folder itself
		"""
		if not self.name or not self.employer:
			return
		
		try:
			employer = frappe.get_doc("Employer", self.employer)
			team = employer.get_drive_team()
			if not team:
				return
			
			employer_folder = employer.get_employer_drive_folder()
			if not employer_folder:
				return
			
			# Find Demands folder
			demands_folder = self.get_drive_folder_by_title("Demands", employer_folder, team)
			if not demands_folder:
				return
			
			# Find Demand folder by demand_reference_no (search in folder title)
			# Get field names from meta
			meta = frappe.get_meta("Demand")
			demand_title_field = meta.get_field("demand_title").fieldname if meta.get_field("demand_title") else "demand_title"
			demand_reference_no_field = meta.get_field("demand_reference_no").fieldname if meta.get_field("demand_reference_no") else "demand_reference_no"
			
			demand_title_value = self.get(demand_title_field) or ""
			demand_reference_no_value = self.get(demand_reference_no_field) or self.name
			
			# Try to find by full format first
			demand_folder = None
			if demand_title_value and demand_reference_no_value:
				folder_name = f"{demand_title_value}-{demand_reference_no_value}"
				folder_name = employer.sanitize_folder_name(folder_name)
				demand_folder = self.get_drive_folder_by_title(folder_name, demands_folder, team)
			
			# Fallback: search by demand_reference_no
			if not demand_folder and demand_reference_no_value:
				all_folders = frappe.get_all(
					"Drive File",
					filters={
						"parent_entity": demands_folder,
						"is_group": 1,
						"is_active": 1,
						"team": team
					},
					fields=["name", "title"]
				)
				for folder in all_folders:
					if folder.get("title", "").endswith(f"-{demand_reference_no_value}") or folder.get("title", "") == demand_reference_no_value:
						demand_folder = folder.get("name")
						break
			
			if demand_folder:
				# Recursively delete the folder
				self.delete_drive_folder_recursive(demand_folder)
				
		except Exception as e:
			frappe.log_error(
				f"Error deleting Drive folders for Demand {self.name}: {str(e)}\n{frappe.get_traceback()}",
				"Demand Drive Folder Deletion Error"
			)
	
	def delete_drive_file_by_url(self, file_url, subfolder_name, demand_folder, team):
		"""
		Function: delete_drive_file_by_url
		Purpose: Delete a Drive file when a document is replaced
		Parameters:
			- file_url: Old file URL
			- subfolder_name: Subfolder where the file should be
			- demand_folder: Demand's main Drive folder name
			- team: Drive team name
		"""
		if not file_url:
			return
		
		try:
			# Find File document
			file_doc = self.find_file_document_by_url(file_url)
			if not file_doc:
				return
			
			# Find subfolder
			subfolder = self.get_drive_folder_by_title(subfolder_name, demand_folder, team)
			if not subfolder:
				return
			
			# Find Drive File in the subfolder
			drive_file_name = frappe.db.get_value(
				"Drive File",
				{
					"title": file_doc.file_name,
					"parent_entity": subfolder,
					"team": team,
					"is_active": 1,
					"is_group": 0
				},
				"name"
			)
			
			if drive_file_name:
				try:
					drive_file_doc = frappe.get_doc("Drive File", drive_file_name)
					# Soft delete (mark as inactive)
					drive_file_doc.is_active = 0
					drive_file_doc.save(ignore_permissions=True)
				except Exception as e:
					frappe.log_error(
						f"Error deleting old Drive file {drive_file_name}: {str(e)}",
						"Drive File Deletion Error"
					)
		except Exception as e:
			frappe.log_error(
				f"Error deleting Drive file by URL {file_url}: {str(e)}",
				"Drive File Deletion Error"
			)
	
	def delete_drive_folder_recursive(self, folder_name):
		"""
		Function: delete_drive_folder_recursive
		Purpose: Recursively delete a Drive folder and all its contents
		Parameters:
			- folder_name: Drive File document name
		"""
		try:
			folder_doc = frappe.get_doc("Drive File", folder_name)
			
			if not folder_doc.is_group:
				# Not a folder, just delete it
				folder_doc.is_active = 0
				folder_doc.save(ignore_permissions=True)
				return
			
			# Get all children
			children = frappe.get_all(
				"Drive File",
				filters={
					"parent_entity": folder_name,
					"is_active": 1
				},
				fields=["name", "is_group"]
			)
			
			# Recursively delete all children
			for child in children:
				if child.is_group:
					self.delete_drive_folder_recursive(child.name)
				else:
					child_doc = frappe.get_doc("Drive File", child.name)
					child_doc.is_active = 0
					child_doc.save(ignore_permissions=True)
			
			# Delete the folder itself
			folder_doc.is_active = 0
			folder_doc.save(ignore_permissions=True)
			
		except frappe.DoesNotExistError:
			# Already deleted, ignore
			pass
		except Exception as e:
			frappe.log_error(
				f"Error deleting Drive folder {folder_name}: {str(e)}\n{frappe.get_traceback()}",
				"Drive Folder Deletion Error"
			)
