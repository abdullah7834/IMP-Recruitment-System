# Copyright (c) 2026, abdullahjavaid198@gmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
import re


class Employer(Document):
	def validate(self):
		"""
		Function: validate
		Purpose: Main validation method called by Frappe framework before saving the document
		Operation: Executes all validation methods in the correct order:
			1. Company Registration Number uniqueness validation
			2. Company Registration Number format validation (if needed)
		"""
		self.validate_unique_company_reg_no()
	
	def validate_unique_company_reg_no(self):
		"""
		Function: validate_unique_company_reg_no
		Purpose: Validates that Company Registration Number is unique across all Employer records
		Operation:
			- Checks database for existing Employer with same company_reg_no
			- Excludes current document from the check (for updates)
			- Throws DuplicateEntryError if company_reg_no already exists
		Trigger: Called during document validation before save
		"""
		if not self.company_reg_no:
			frappe.throw(
				_("Company Registration Number is required."),
				title=_("Validation Error")
			)
		
		existing = frappe.db.exists(
			"Employer",
			{
				"company_reg_no": self.company_reg_no,
				"name": ["!=", self.name]
			}
		)
		
		if existing:
			frappe.throw(
				_("Employer with Company Registration Number {0} already exists.").format(self.company_reg_no),
				frappe.DuplicateEntryError
			)
	
	def after_insert(self):
		"""
		Function: after_insert
		Purpose: Create Drive folder structure when Employer is first created
		Operation: Calls create_employer_drive_structure() to set up all folders and company info file
		Trigger: Called automatically after document is inserted into database
		"""
		# Create folder structure (non-blocking - errors are logged but don't prevent Employer creation)
		result = self.create_employer_drive_structure()
		
		# Only create company info file if folder structure was created successfully
		if result:
			self.create_or_update_company_info_file()
		else:
			# Log warning but don't block
			frappe.log_error(
				f"Drive folder structure creation failed for Employer {self.name}. Company info file will not be created.",
				"Employer Drive Folder Creation Warning"
			)
	
	def on_update(self):
		"""
		Function: on_update
		Purpose: Handle folder rename when employer_name changes, process document files, and update company info
		Operation:
			- Checks if employer_name changed
			- Renames folder if name changed (preserves all subfolders and files)
			- Ensures folder structure exists (creates if missing)
			- Processes any document files from child table
			- Updates company info file if any relevant fields changed
			- This runs after child table rows are saved, ensuring File documents are created
		Trigger: Called automatically when document is updated
		"""
		# Check if employer_name changed (affects folder name)
		if self.has_value_changed("employer_name") and self.employer_name:
			self.rename_employer_folder()
		
		# Ensure folder structure exists (in case it wasn't created on insert) - idempotent
		if self.employer_name:
			self.create_employer_drive_structure()
		
		# Process files from child table (runs after child table rows are saved)
		if self.employer_name:
			self.process_employer_document_files()
		
		# Update company info file if any relevant fields changed
		if self.has_company_info_changed():
			self.create_or_update_company_info_file()
	
	def on_trash(self):
		"""
		Function: on_trash
		Purpose: Delete Employer Drive folder when Employer is deleted
		Operation:
			- Checks for force_delete flag (from document field, database, frappe.flags, or frappe.form_dict)
			- If force_delete is True, deletes entire folder structure
			- If force_delete is False or not set, blocks deletion with error
		Trigger: Called automatically before document is deleted from database
		"""
		# Check for force_delete flag from multiple sources
		# Priority: frappe.flags > frappe.form_dict > document field > database value
		force_delete = False
		field_exists_in_db = False
		
		# First, check if field exists in database (for migration compatibility)
		try:
			meta = frappe.get_meta("Employer")
			if meta.has_field("force_delete"):
				field_exists_in_db = frappe.db.has_column("Employer", "force_delete")
		except Exception:
			pass
		
		# If field doesn't exist in DB yet (migration not run), allow deletion for backward compatibility
		if not field_exists_in_db:
			# Field not migrated yet, allow deletion (backward compatibility)
			force_delete = True
		else:
			# Field exists, check all sources
			# Check frappe.flags first (for programmatic deletions with explicit flag)
			if frappe.flags.get("force_delete") is not None:
				force_delete = bool(frappe.flags.get("force_delete"))
			
			# Check frappe.form_dict (for API deletions)
			if not force_delete and frappe.form_dict.get("force_delete") is not None:
				force_delete = bool(frappe.form_dict.get("force_delete"))
			
			# Check document field (if loaded in form)
			if not force_delete and hasattr(self, 'force_delete'):
				force_delete = bool(self.force_delete)
			
			# Check database value (for list view deletions)
			if not force_delete:
				try:
					db_value = frappe.db.get_value("Employer", self.name, "force_delete")
					if db_value is not None:
						force_delete = bool(db_value)
				except Exception as e:
					# Error reading from database, log and block deletion for safety
					frappe.log_error(
						f"Error reading force_delete field for Employer {self.name}: {str(e)}",
						"Employer Delete Check Error"
					)
					force_delete = False
		
		if not force_delete:
			frappe.throw(
				_("Cannot delete Employer. Please open the Employer record, check the 'Allow Deletion (Delete Drive Folders)' checkbox, save the record, then try deleting again."),
				title=_("Deletion Blocked")
			)
		
		# Delete folder structure
		# Use try-except to ensure Employer deletion succeeds even if Drive deletion fails
		try:
			self.delete_employer_drive_folders()
		except Exception as e:
			# Log error but don't prevent Employer deletion
			frappe.log_error(
				f"Error deleting Drive folders for Employer {self.name} during deletion: {str(e)}\n{frappe.get_traceback()}",
				"Employer Drive Folder Deletion Error"
			)
	
	def create_employer_drive_structure(self):
		"""
		Function: create_employer_drive_structure
		Purpose: Create the complete Drive folder structure for an Employer using Frappe Drive
		Operation:
			1. Get user's default Drive team
			2. Get home folder for the team
			3. Create /Employers/ root folder (if not exists)
			4. Create individual Employer folder: {employer_name}
			5. Create all required subfolders: Legal/MOU, Legal/POA, Legal/Contracts, Legal/Licenses, Demands, Job_Openings, Batches
		Returns: True if successful, False otherwise
		"""
		if not self.employer_name:
			# Don't log error if fields are just not filled yet (during form editing)
			return False
		
		try:
			# Check if Drive app is installed
			if not frappe.db.exists("DocType", "Drive File"):
				frappe.log_error(
					"Drive app is not installed. Please install the Drive app to enable folder creation.",
					"Employer Drive Folder Creation Error"
				)
				return False
			
			# Get user's default Drive team
			team = self.get_drive_team()
			if not team:
				error_msg = f"No Drive team found for user {frappe.session.user}. Please create a Drive Team first. You can create one by accessing Drive in the app."
				frappe.log_error(
					error_msg,
					"Employer Drive Folder Creation Error"
				)
				# Show user-friendly message if not in background/import mode
				if not frappe.flags.in_import and not frappe.flags.in_migrate and not frappe.flags.in_install:
					try:
						frappe.msgprint(
							_("No Drive team found. Please access Drive app first to create a team, then try again."),
							title=_("Drive Setup Required"),
							indicator="orange"
						)
					except Exception:
						pass
				# Re-raise error for whitelisted methods so user knows what went wrong
				if hasattr(frappe.local, 'request') and frappe.request.path.startswith('/api/method'):
					frappe.throw(_(error_msg), title=_("Drive Setup Required"))
				return False
			
			# Get home folder for the team
			home_folder = self.get_home_folder(team)
			if not home_folder:
				frappe.log_error(
					f"Home folder not found for team {team}",
					"Employer Drive Folder Creation Error"
				)
				return False
			
			# Sanitize folder name using format: "{employer_name}-{company_reg_no}"
			# Get field names from meta to avoid hardcoding
			meta = frappe.get_meta("Employer")
			employer_name_field = meta.get_field("employer_name").fieldname if meta.get_field("employer_name") else "employer_name"
			company_reg_no_field = meta.get_field("company_reg_no").fieldname if meta.get_field("company_reg_no") else "company_reg_no"
			
			employer_name_value = self.get(employer_name_field) or ""
			company_reg_no_value = self.get(company_reg_no_field) or ""
			
			if not employer_name_value or not company_reg_no_value:
				frappe.log_error(
					f"Missing required fields for folder creation: employer_name={employer_name_value}, company_reg_no={company_reg_no_value}",
					"Employer Drive Folder Creation Error"
				)
				return False
			
			# Format: "{employer_name}-{company_reg_no}"
			folder_name = f"{employer_name_value}-{company_reg_no_value}"
			folder_name = self.sanitize_folder_name(folder_name)
			
			# Ensure folder name doesn't exceed limit (140 chars)
			if len(folder_name) > 140:
				folder_name = folder_name[:137] + "..."
			
			# Step 1: Get or create main /Employers/ root folder
			employers_root = self.get_or_create_drive_folder("Employers", home_folder, team)
			if not employers_root:
				frappe.log_error(
					f"Failed to create/get 'Employers' root folder in home folder '{home_folder}' for team '{team}'",
					"Employer Drive Folder Creation Error"
				)
				return False
			
			# Step 2: Get or create individual Employer folder inside /Employers/
			# Check if folder already exists (reuse existing folder for duplicate creation attempts)
			employer_folder = self.get_drive_folder_by_title(folder_name, employers_root, team)
			if not employer_folder:
				employer_folder = self.get_or_create_drive_folder(folder_name, employers_root, team)
				# Verify folder was actually created
				if not employer_folder:
					# Try one more time to get it (in case of race condition)
					employer_folder = self.get_drive_folder_by_title(folder_name, employers_root, team)
			
			if not employer_folder:
				error_msg = f"Failed to create/get Employer folder '{folder_name}' in 'Employers' root for team '{team}'. Employers root: {employers_root}"
				frappe.log_error(
					error_msg,
					"Employer Drive Folder Creation Error"
				)
				# Re-raise error for whitelisted methods so user knows what went wrong
				if hasattr(frappe.local, 'request') and frappe.request.path.startswith('/api/method'):
					frappe.throw(_(error_msg), title=_("Folder Creation Failed"))
				return False
			
			# Store folder reference in drive_root_folder field (if field exists)
			# Use db_set to avoid recursion during insert
			if hasattr(self, 'drive_root_folder') or frappe.db.has_column("Employer", "drive_root_folder"):
				try:
					self.db_set("drive_root_folder", employer_folder, update_modified=False)
				except Exception:
					# Field might not exist yet, ignore
					pass
			
			# Step 3: Create all required subfolders according to specification
			# Structure: /Employers/{Employer Name}/
			#   - /Legal/
			#     - /MOU/
			#     - /POA/
			#     - /Contracts/
			#     - /Licenses/
			#   - /Demands/
			#   - /Job_Openings/
			#   - /Batches/
			
			# Create Legal folder and its subfolders
			legal_folder = self.get_or_create_drive_folder("Legal", employer_folder, team)
			if legal_folder:
				self.get_or_create_drive_folder("MOU", legal_folder, team)
				self.get_or_create_drive_folder("POA", legal_folder, team)
				self.get_or_create_drive_folder("Contracts", legal_folder, team)
				self.get_or_create_drive_folder("Licenses", legal_folder, team)
			
			# Create direct subfolders
			self.get_or_create_drive_folder("Demands", employer_folder, team)
			self.get_or_create_drive_folder("Job_Openings", employer_folder, team)
			self.get_or_create_drive_folder("Batches", employer_folder, team)
			
			# Only show message if not in import/API mode and not in background
			if not frappe.flags.in_import and not frappe.flags.in_migrate and not frappe.flags.in_install:
				# Use frappe.publish_realtime for non-blocking message
				try:
					frappe.publish_realtime(
						"drive_folders_created",
						{"message": _("Drive folders created successfully for {0}").format(self.employer_name)},
						user=frappe.session.user
					)
				except Exception:
					# Ignore realtime publish errors
					pass
			
			return True
			
		except Exception as e:
			# Log detailed error information
			error_details = {
				"employer_name": self.employer_name,
				"company_reg_no": self.company_reg_no,
				"employer_id": self.name,
				"user": frappe.session.user,
				"error": str(e),
				"traceback": frappe.get_traceback()
			}
			frappe.log_error(
				f"Error creating Drive folders for Employer {self.name} (Name: {self.employer_name}): {str(e)}\n{frappe.get_traceback()}\nDetails: {error_details}",
				"Employer Drive Folder Creation Error"
			)
			# Don't throw error - allow Employer creation to succeed even if folder creation fails
			return False
	
	def rename_employer_folder(self):
		"""
		Function: rename_employer_folder
		Purpose: Rename Employer folder when employer_name or company_reg_no changes
		Operation:
			- Gets old values from database
			- Finds existing folder using drive_root_folder or by company_reg_no
			- Renames folder to new name: "{employer_name}-{company_reg_no}"
			- Preserves all subfolders and files
			- Updates drive_root_folder reference
		"""
		# Get field names from meta to avoid hardcoding
		meta = frappe.get_meta("Employer")
		employer_name_field = meta.get_field("employer_name").fieldname if meta.get_field("employer_name") else "employer_name"
		company_reg_no_field = meta.get_field("company_reg_no").fieldname if meta.get_field("company_reg_no") else "company_reg_no"
		
		employer_name_value = self.get(employer_name_field) or ""
		company_reg_no_value = self.get(company_reg_no_field) or ""
		
		if not employer_name_value or not company_reg_no_value:
			return
		
		try:
			# Get old values from database (before update)
			old_employer_name = frappe.db.get_value("Employer", self.name, employer_name_field)
			old_company_reg_no = frappe.db.get_value("Employer", self.name, company_reg_no_field)
			
			# Build old and new folder names
			old_folder_name = None
			if old_employer_name and old_company_reg_no:
				old_folder_name = f"{old_employer_name}-{old_company_reg_no}"
				old_folder_name = self.sanitize_folder_name(old_folder_name)
			
			new_folder_name = f"{employer_name_value}-{company_reg_no_value}"
			new_folder_name = self.sanitize_folder_name(new_folder_name)
			
			# Ensure new folder name doesn't exceed limit
			if len(new_folder_name) > 140:
				new_folder_name = new_folder_name[:137] + "..."
			
			if not old_folder_name or old_folder_name == new_folder_name:
				return  # No change or no old name
			
			team = self.get_drive_team()
			if not team:
				return
			
			home_folder = self.get_home_folder(team)
			if not home_folder:
				return
			
			# Find Employers root folder
			employers_root = self.get_drive_folder_by_title("Employers", home_folder, team)
			if not employers_root:
				return
			
			# Try to get folder from drive_root_folder first
			old_folder = None
			if hasattr(self, 'drive_root_folder') and self.drive_root_folder:
				try:
					folder_doc = frappe.get_doc("Drive File", self.drive_root_folder)
					if folder_doc.is_group and folder_doc.is_active:
						old_folder = self.drive_root_folder
				except frappe.DoesNotExistError:
					pass
			
			# If not found, find by old name or by old company_reg_no
			if not old_folder:
				old_folder = self.get_drive_folder_by_title(old_folder_name, employers_root, team)
			
			# If still not found, try searching by old company_reg_no
			if not old_folder and old_company_reg_no:
				all_folders = frappe.get_all(
					"Drive File",
					filters={
						"parent_entity": employers_root,
						"is_group": 1,
						"is_active": 1,
						"team": team
					},
					fields=["name", "title"]
				)
				for folder in all_folders:
					if folder.get("title", "").endswith(f"-{old_company_reg_no}") or folder.get("title", "") == old_company_reg_no:
						old_folder = folder.get("name")
						break
			
			if old_folder:
				# Rename folder
				self.rename_drive_folder(old_folder, new_folder_name, team)
				
				# Update drive_root_folder reference
				updated_folder = self.get_drive_folder_by_title(new_folder_name, employers_root, team)
				if updated_folder:
					self.db_set("drive_root_folder", updated_folder, update_modified=False)
			
		except Exception as e:
			frappe.log_error(
				f"Error renaming Drive folder for Employer {self.name}: {str(e)}\n{frappe.get_traceback()}",
				"Employer Drive Folder Rename Error"
			)
	
	def delete_employer_drive_folders(self):
		"""
		Function: delete_employer_drive_folders
		Purpose: Delete the entire Drive folder structure for an Employer
		Operation:
			1. Find the Employer's main folder using drive_root_folder or "{employer_name}"
			2. Recursively delete all files and subfolders
			3. Delete the main folder itself
		"""
		if not self.employer_name:
			return
		
		try:
			team = self.get_drive_team()
			if not team:
				return
			
			home_folder = self.get_home_folder(team)
			if not home_folder:
				return
			
			# Find Employers root folder
			employers_root = self.get_drive_folder_by_title("Employers", home_folder, team)
			if not employers_root:
				return
			
			# Try to get folder from drive_root_folder first
			employer_folder = None
			if hasattr(self, 'drive_root_folder') and self.drive_root_folder:
				try:
					folder_doc = frappe.get_doc("Drive File", self.drive_root_folder)
					if folder_doc.is_group and folder_doc.is_active:
						employer_folder = self.drive_root_folder
				except frappe.DoesNotExistError:
					pass
			
			# If not found, find by company_reg_no (search in folder title)
			if not employer_folder:
				# Get field names from meta
				meta = frappe.get_meta("Employer")
				company_reg_no_field = meta.get_field("company_reg_no").fieldname if meta.get_field("company_reg_no") else "company_reg_no"
				company_reg_no_value = self.get(company_reg_no_field) or ""
				
				if company_reg_no_value:
					# Search all folders in Employers root and find one that ends with company_reg_no
					all_folders = frappe.get_all(
						"Drive File",
						filters={
							"parent_entity": employers_root,
							"is_group": 1,
							"is_active": 1,
							"team": team
						},
						fields=["name", "title"]
					)
					
					for folder in all_folders:
						# Check if folder title ends with company_reg_no
						if folder.get("title", "").endswith(f"-{company_reg_no_value}") or folder.get("title", "") == company_reg_no_value:
							employer_folder = folder.get("name")
							break
			
			if employer_folder:
				# Recursively delete the folder
				self.delete_drive_folder_recursive(employer_folder)
				
		except Exception as e:
			frappe.log_error(
				f"Error deleting Drive folders for Employer {self.name}: {str(e)}\n{frappe.get_traceback()}",
				"Employer Drive Folder Deletion Error"
			)
	
	def get_drive_team(self):
		"""
		Function: get_drive_team
		Purpose: Get the user's default Drive team
		Returns: Team name (string) or None
		"""
		try:
			# Try using Drive's default team utility first
			try:
				from drive.utils import get_default_team
				team = get_default_team()
				if team:
					return team
			except Exception:
				pass
			
			# Try to get personal team first
			team = frappe.db.get_value("Drive Team", {"owner": frappe.session.user, "personal": 1}, "name")
			if team:
				return team
			
			# If no personal team, get any team where user is a member
			team = frappe.db.get_value(
				"Drive Team Member",
				{"user": frappe.session.user},
				"parent",
				order_by="creation desc"
			)
			return team
		except Exception as e:
			frappe.log_error(
				f"Error getting Drive team for user {frappe.session.user}: {str(e)}",
				"Drive Team Lookup Error"
			)
			return None
	
	def get_home_folder(self, team):
		"""
		Function: get_home_folder
		Purpose: Get the home folder for a Drive team
		Parameters:
			- team: Drive team name
		Returns: Drive File document name (string) or None
		"""
		try:
			from drive.utils import get_home_folder
			home_folder = get_home_folder(team)
			return home_folder.name if home_folder else None
		except Exception:
			return None
	
	def get_or_create_drive_folder(self, title, parent_entity, team):
		"""
		Function: get_or_create_drive_folder
		Purpose: Get existing Drive folder or create it if it doesn't exist (idempotent)
		Parameters:
			- title: Folder title/name
			- parent_entity: Parent Drive File document name
			- team: Drive team name
		Returns: Drive File document name (string) or None
		"""
		if not title or not parent_entity or not team:
			frappe.log_error(
				f"Invalid parameters for get_or_create_drive_folder: title={title}, parent={parent_entity}, team={team}",
				"Drive Folder Creation Error"
			)
			return None
		
		# Check if folder already exists (idempotent check)
		existing_folder = frappe.db.get_value(
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
		
		if existing_folder:
			return existing_folder
		
		# Create new folder using Drive API
		try:
			# Try using Drive's create_folder API first (more reliable)
			try:
				from drive.api.files import create_folder
				from drive.api.permissions import user_has_permission
				
				# Check permissions first
				try:
					parent_doc_check = frappe.get_doc("Drive File", parent_entity)
					if not user_has_permission(parent_doc_check, "upload"):
						# Try to grant permission or use manual method
						frappe.log_error(
							f"No upload permission on parent folder '{parent_entity}' for user '{frappe.session.user}'. Trying manual method.",
							"Drive Folder Creation Permission Warning"
						)
						raise PermissionError("No upload permission")
					
					# Call create_folder API
					drive_file = create_folder(team=team, title=title, parent=parent_entity)
					if drive_file and hasattr(drive_file, 'name') and drive_file.name:
						# Verify it was actually created
						created_folder = frappe.db.get_value(
							"Drive File",
							{"name": drive_file.name, "is_active": 1},
							"name"
						)
						if created_folder:
							return created_folder
				except (PermissionError, frappe.PermissionError) as perm_error:
					# Permission issue, fall through to manual method
					frappe.log_error(
						f"Permission error creating folder '{title}': {str(perm_error)}. Trying manual method.",
						"Drive Folder Creation Permission Warning"
					)
				except FileExistsError:
					# Folder already exists, try to get it
					existing_folder = frappe.db.get_value(
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
					if existing_folder:
						return existing_folder
					# If not found, continue to manual method
				except Exception as api_error:
					# If API fails, fall back to manual creation
					error_msg = str(api_error)
					error_type = type(api_error).__name__
					# Don't log if it's just a "folder exists" error (handled by idempotent check)
					if "already exists" not in error_msg.lower() and "file exists" not in error_msg.lower():
						frappe.log_error(
							f"Drive API create_folder failed for '{title}' (type: {error_type}): {error_msg}. Trying manual method.",
							"Drive Folder Creation Warning"
						)
			except ImportError:
				# Drive API not available, use manual method
				frappe.log_error(
					"Drive API not available, using manual folder creation method",
					"Drive Folder Creation Info"
				)
			
			# Fallback: Manual folder creation with better error handling
			try:
				from pathlib import Path
				from drive.utils import create_drive_file, if_folder_exists
				from drive.utils.files import FileManager
				from drive.utils import get_home_folder
				
				# Get parent folder document
				try:
					parent_doc = frappe.get_doc("Drive File", parent_entity)
				except frappe.DoesNotExistError:
					frappe.log_error(
						f"Parent folder '{parent_entity}' does not exist",
						"Drive Folder Creation Error"
					)
					return None
				
				home_folder = get_home_folder(team)
				
				if not home_folder:
					frappe.log_error(
						f"Home folder not found for team {team}",
						"Drive Folder Creation Error"
					)
					return None
				
				# Try using if_folder_exists utility first (simpler, handles permissions better)
				# This utility creates the folder if it doesn't exist, or returns existing one
				try:
					existing_or_new_folder = if_folder_exists(team, title, parent_entity)
					if existing_or_new_folder:
						# Verify it's active and is a folder
						try:
							folder_doc = frappe.get_doc("Drive File", existing_or_new_folder)
							if folder_doc.is_active and folder_doc.is_group:
								return existing_or_new_folder
							else:
								frappe.log_error(
									f"Folder '{existing_or_new_folder}' found but not active or not a folder. is_active={folder_doc.is_active}, is_group={folder_doc.is_group}",
									"Drive Folder Creation Warning"
								)
						except frappe.DoesNotExistError:
							# Folder was created but document doesn't exist yet, wait a moment and retry
							frappe.db.commit()  # Ensure DB is committed
							existing_folder = frappe.db.get_value(
								"Drive File",
								{"name": existing_or_new_folder, "is_active": 1, "is_group": 1},
								"name"
							)
							if existing_folder:
								return existing_folder
				except Exception as util_error:
					error_msg = str(util_error)
					frappe.log_error(
						f"if_folder_exists utility failed for '{title}' in parent '{parent_entity}': {error_msg}. Trying FileManager method.",
						"Drive Folder Creation Warning"
					)
				
				# Create folder path using FileManager
				manager = FileManager()
				parent_path = Path(parent_doc.path) if parent_doc.path else Path("")
				
				path = manager.create_folder(
					frappe._dict({
						"title": title,
						"team": team,
						"parent_path": parent_path,
					}),
					home_folder,
				)
				
				# Create Drive File document
				drive_file = create_drive_file(
					team=team,
					title=title,
					parent=parent_entity,
					mime_type="folder",
					entity_path=lambda _: path,
					is_group=True,
				)
				
				if drive_file and drive_file.name:
					# Verify it was created and is active
					created_folder = frappe.db.get_value(
						"Drive File",
						{"name": drive_file.name, "is_active": 1, "is_group": 1},
						"name"
					)
					if created_folder:
						return created_folder
					else:
						frappe.log_error(
							f"Drive file '{drive_file.name}' created but not found as active folder",
							"Drive Folder Creation Error"
						)
						return None
				else:
					frappe.log_error(
						f"Drive file created but name is None for folder '{title}'",
						"Drive Folder Creation Error"
					)
					return None
			except Exception as manual_error:
				# Log the manual creation error but don't fail yet
				error_msg = str(manual_error)
				frappe.log_error(
					f"Manual folder creation failed for '{title}' in parent '{parent_entity}': {error_msg}\n{frappe.get_traceback()}",
					"Drive Folder Creation Error"
				)
				# Try one more time to see if folder was created despite error
				existing_folder = frappe.db.get_value(
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
				if existing_folder:
					return existing_folder
				# Re-raise to be caught by outer exception handler
				raise
			
		except Exception as e:
			error_str = str(e).lower()
			
			# Handle "File exists" error gracefully (idempotent)
			if "file exists" in error_str or "errno 17" in error_str or "already exists" in error_str or "folder" in error_str and "exists" in error_str:
				# Try to get the existing folder again
				existing_folder = frappe.db.get_value(
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
				if existing_folder:
					return existing_folder
			
			# For other errors, try to get existing folder one more time (race condition)
			existing_folder = frappe.db.get_value(
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
			if existing_folder:
				return existing_folder
			
			# Log error with full details
			frappe.log_error(
				f"Error creating Drive folder '{title}' in parent '{parent_entity}' for team '{team}': {str(e)}\n{frappe.get_traceback()}",
				"Drive Folder Creation Error"
			)
			# Return None instead of raising - allows graceful degradation
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
	
	def sanitize_folder_name(self, name):
		"""
		Function: sanitize_folder_name
		Purpose: Sanitize folder name by removing invalid characters and ensuring length limits
		Operation:
			- Uses employer_name exactly as stored
			- Replaces "/" with "-"
			- Trims extra spaces
			- Truncates to 140 characters (Drive limit)
		Returns: Sanitized folder name string
		"""
		if not name:
			return ""
		
		# Use name exactly as stored, replace "/" with "-"
		sanitized = str(name).replace("/", "-")
		
		# Replace multiple spaces with single space
		sanitized = re.sub(r'\s+', ' ', sanitized)
		
		# Trim whitespace
		sanitized = sanitized.strip()
		
		# Truncate to 140 characters (Drive folder name limit)
		if len(sanitized) > 140:
			sanitized = sanitized[:137] + "..."
		
		return sanitized
	
	def get_employer_drive_folder(self):
		"""
		Function: get_employer_drive_folder
		Purpose: Get the main Drive folder for this Employer
		Operation:
			- First tries to get from drive_root_folder field
			- Falls back to finding folder by "{employer_name}-{company_reg_no}" or by company_reg_no
		Returns: Drive File document name (string) or None
		"""
		# Get field names from meta to avoid hardcoding
		meta = frappe.get_meta("Employer")
		employer_name_field = meta.get_field("employer_name").fieldname if meta.get_field("employer_name") else "employer_name"
		company_reg_no_field = meta.get_field("company_reg_no").fieldname if meta.get_field("company_reg_no") else "company_reg_no"
		
		employer_name_value = self.get(employer_name_field) or ""
		company_reg_no_value = self.get(company_reg_no_field) or ""
		
		if not company_reg_no_value:
			return None
		
		# Try to get from drive_root_folder first
		if hasattr(self, 'drive_root_folder') and self.drive_root_folder:
			try:
				folder_doc = frappe.get_doc("Drive File", self.drive_root_folder)
				if folder_doc.is_group and folder_doc.is_active:
					return self.drive_root_folder
			except frappe.DoesNotExistError:
				pass
		
		# Fallback: find folder by company_reg_no (search in folder title)
		try:
			team = self.get_drive_team()
			if not team:
				return None
			
			home_folder = self.get_home_folder(team)
			if not home_folder:
				return None
			
			# Get Employers root folder
			employers_root = self.get_drive_folder_by_title("Employers", home_folder, team)
			if not employers_root:
				return None
			
			# Try to find folder by full format: "{employer_name}-{company_reg_no}"
			if employer_name_value:
				folder_name = f"{employer_name_value}-{company_reg_no_value}"
				folder_name = self.sanitize_folder_name(folder_name)
				found_folder = self.get_drive_folder_by_title(folder_name, employers_root, team)
				if found_folder:
					return found_folder
			
			# Fallback: search by company_reg_no in folder title (more reliable since it's the ID)
			# Search all folders in Employers root and find one that ends with company_reg_no
			all_folders = frappe.get_all(
				"Drive File",
				filters={
					"parent_entity": employers_root,
					"is_group": 1,
					"is_active": 1,
					"team": team
				},
				fields=["name", "title"]
			)
			
			for folder in all_folders:
				# Check if folder title ends with company_reg_no
				if folder.get("title", "").endswith(f"-{company_reg_no_value}") or folder.get("title", "") == company_reg_no_value:
					return folder.get("name")
			
			return None
			
		except Exception as e:
			frappe.log_error(
				f"Error getting Drive folder for Employer {self.name}: {str(e)}",
				"Employer Drive Folder Lookup Error"
			)
			return None
	
	def get_all_document_types(self):
		"""
		Function: get_all_document_types
		Purpose: Get all document types from Employer Document DocType dynamically
		Operation: Reads document_type options from Employer Document DocType meta
		Returns: List of document type strings
		"""
		try:
			# Get document type options from Employer Document DocType
			doc_type_meta = frappe.get_meta("Employer Document")
			document_type_field = doc_type_meta.get_field("document_type")
			
			if document_type_field and document_type_field.options:
				# Split options by newline
				options = document_type_field.options.split("\n")
				# Filter out empty strings and return list
				return [opt.strip() for opt in options if opt.strip()]
			
			# Fallback to default list if meta not available
			return ["MOU", "POA", "Contract", "Commercial Registration", "License", "NDA", "Other"]
		except Exception as e:
			frappe.log_error(
				f"Error getting document types: {str(e)}",
				"Employer Document Types Error"
			)
			# Return default list on error
			return ["MOU", "POA", "Contract", "Commercial Registration", "License", "NDA", "Other"]
	
	def get_document_folder_structure(self):
		"""
		Function: get_document_folder_structure
		Purpose: Get folder structure mapping for all document types
		Operation: Maps document types to their parent folders and subfolders
		Returns: Dictionary with parent_folder as key and list of subfolders as value
		"""
		# Define folder structure according to specification:
		# /Employers/{Employer Name}/
		#   - /Legal/
		#     - /MOU/
		#     - /POA/
		#     - /Contracts/
		#     - /Licenses/
		#   - /Demands/
		#   - /Job_Openings/
		#   - /Batches/
		structure = {
			"Legal": ["MOU", "POA", "Contracts", "Licenses"],
			"": ["Demands", "Job_Openings", "Batches"]
		}
		
		return structure
	
	def get_document_subfolder(self, document_type):
		"""
		Function: get_document_subfolder
		Purpose: Get the appropriate subfolder mapping for a document type
		Operation:
			- Maps each document type to its corresponding Drive subfolder
			- MOU → /Legal/MOU/
			- POA → /Legal/POA/
			- Contract → /Legal/Contracts/
			- License → /Legal/Licenses/
			- Other documents go to Demands folder
		Parameters:
			- document_type: Document type string from dropdown
		Returns: Tuple of (parent_folder_name, subfolder_name) or None
			- parent_folder_name can be None or "" for root level folders
		"""
		if not document_type:
			return None
		
		# Normalize document_type (strip whitespace, handle case)
		document_type = str(document_type).strip()
		
		# Document type to folder mapping according to specification
		# Format: document_type -> (parent_folder, subfolder_name)
		mapping = {
			"MOU": ("Legal", "MOU"),
			"POA": ("Legal", "POA"),
			"Contract": ("Legal", "Contracts"),
			"License": ("Legal", "Licenses"),
		}
		
		# Return mapping if exists
		if document_type in mapping:
			parent, subfolder = mapping[document_type]
			return (parent, subfolder)
		
		# Default: put in Demands folder for unmapped document types
		return (None, "Demands")
	
	def process_employer_document_files(self):
		"""
		Function: process_employer_document_files
		Purpose: Process files from Employer Document child table and move them to correct Drive subfolders
		Operation:
			- Ensures folder structure exists (creates if missing)
			- Gets all saved employer_document rows from database
			- For each row with a file, finds the correct subfolder based on document_type
			- Creates or moves Drive File entry to the correct location
			- This runs after child table rows are saved, ensuring File documents are created
		"""
		if not self.employer_name:
			return
		
		# Ensure folder structure exists (in case it wasn't created on insert)
		if not self.create_employer_drive_structure():
			# Folder creation failed, but continue to try processing files
			pass
		
		team = self.get_drive_team()
		if not team:
			return
		
		employer_folder_name = self.get_employer_drive_folder()
		if not employer_folder_name:
			# Try to create folder structure again
			self.create_employer_drive_structure()
			employer_folder_name = self.get_employer_drive_folder()
			if not employer_folder_name:
				return
		
		# Get all saved employer_document rows from database (not just form)
		saved_documents = frappe.get_all(
			"Employer Document",
			filters={"parent": self.name, "parenttype": "Employer"},
			fields=["name", "document_file", "document_type"]
		)
		
		# Process each document from database
		for doc_data in saved_documents:
			if not doc_data.get("document_file") or not doc_data.get("document_type"):
				continue
			
			try:
				# Get subfolder mapping for this document type
				document_type = doc_data.get("document_type")
				if not document_type:
					continue
				
				subfolder_info = self.get_document_subfolder(document_type)
				if not subfolder_info:
					# Document type not mapped, skip
					continue
				
				parent_folder_name, subfolder_name = subfolder_info
				
				# Determine target folder (parent folder if exists, otherwise employer folder)
				if parent_folder_name:
					# Get or create parent folder (e.g., "Legal")
					parent_folder = self.get_or_create_drive_folder(parent_folder_name, employer_folder_name, team)
					if not parent_folder:
						continue
					target_parent = parent_folder
				else:
					# Direct subfolder under employer folder (e.g., "Demands", "Job_Openings")
					target_parent = employer_folder_name
				
				# Get or create subfolder (MOU, POA, Demands, etc.)
				subfolder_drive = self.get_or_create_drive_folder(subfolder_name, target_parent, team)
				if not subfolder_drive:
					continue
				
				# Find the File document
				file_doc = self.find_file_document_by_url(doc_data.get("document_file"))
				if not file_doc:
					continue
				
				# Create or move Drive File entry
				self.create_or_move_drive_file_for_row(file_doc, subfolder_drive, team)
				
			except Exception as e:
				frappe.log_error(
					f"Error processing file for Employer Document {doc_data.get('name')}: {str(e)}\n{frappe.get_traceback()}",
					"Employer Document File Processing Error"
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
		
		# Method 3: Lookup by attached_to (files attached to parent Employer)
		if not file_name and self.name:
			file_name = frappe.db.get_value(
				"File",
				{
					"attached_to_name": self.name,
					"attached_to_doctype": "Employer",
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
	
	def create_or_move_drive_file_for_row(self, file_doc, parent_folder, team):
		"""
		Function: create_or_move_drive_file_for_row
		Purpose: Create or move a Drive File entry for an uploaded file
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
			import tempfile
			import os
			
			# Check if Drive File already exists for this File document
			existing_drive_file = frappe.db.get_value(
				"Drive File",
				{
					"title": file_doc.file_name,
					"parent_entity": parent_folder,
					"is_active": 1,
					"is_group": 0,
					"team": team
				},
				"name"
			)
			
			if existing_drive_file:
				# Already exists in correct location, skip
				return
			
			# Get home folder
			home_folder = get_home_folder(team)
			if not home_folder:
				frappe.log_error(
					f"Home folder not found for team {team}",
					"Drive File Creation Error"
				)
				return
			
			# Get parent folder document
			parent_doc = frappe.get_doc("Drive File", parent_folder)
			
			# Get file path from File document
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
			
			# Upload file content to Drive storage
			if file_path.exists() and drive_file:
				manager.upload_file(file_path, drive_file, create_thumbnail=True)
				
		except Exception as e:
			frappe.log_error(
				f"Error creating/moving Drive file for File {file_doc.name}: {str(e)}\n{frappe.get_traceback()}",
				"Drive File Creation Error"
			)
	
	def has_company_info_changed(self):
		"""
		Function: has_company_info_changed
		Purpose: Check if any company information fields have changed
		Operation: Checks if any relevant fields that should be in company info file have changed
		Returns: True if any relevant field changed, False otherwise
		"""
		# List of fields that should trigger company info file update
		info_fields = [
			"employer_name", "company_reg_no", "status", "city", "address",
			"employer_code", "country", "website", "primary_contact_name",
			"primary_contact_phone", "primary_contact_designation", "primary_contact_email",
			"preferred_language", "recruitment_active", "default_currency",
			"poa_valid_till", "mou_available", "have_poa", "remarks"
		]
		
		# Check if any of these fields changed
		for field in info_fields:
			if self.has_value_changed(field):
				return True
		
		return False
	
	def create_or_update_company_info_file(self):
		"""
		Function: create_or_update_company_info_file
		Purpose: Create or update a text file in the Employer Drive folder with company information
		Operation:
			- Gets all relevant company information fields
			- Formats them into a readable text file
			- Creates or updates the file in the Employer's Drive folder
			- Updates in real-time when Employer data changes
		"""
		if not self.employer_name or not self.company_reg_no:
			return
		
		try:
			# Get Employer's Drive folder
			employer_folder = self.get_employer_drive_folder()
			if not employer_folder:
				# Try to create folder structure first
				self.create_employer_drive_structure()
				employer_folder = self.get_employer_drive_folder()
				if not employer_folder:
					return
			
			team = self.get_drive_team()
			if not team:
				return
			
			# Generate company information content
			info_content = self.generate_company_info_content()
			
			# File name for company info
			info_file_name = "Company_Information.txt"
			
			# Check if file already exists
			existing_file = frappe.db.get_value(
				"Drive File",
				{
					"title": info_file_name,
					"parent_entity": employer_folder,
					"is_active": 1,
					"is_group": 0,
					"team": team
				},
				"name"
			)
			
			if existing_file:
				# Update existing file
				self.update_drive_file_content(existing_file, info_content, team)
			else:
				# Create new file
				self.create_drive_text_file(info_file_name, employer_folder, info_content, team)
			
		except Exception as e:
			frappe.log_error(
				f"Error creating/updating company info file for Employer {self.name}: {str(e)}\n{frappe.get_traceback()}",
				"Company Info File Error"
			)
	
	def generate_company_info_content(self):
		"""
		Function: generate_company_info_content
		Purpose: Generate formatted text content with company information
		Operation: Collects all relevant fields and formats them into a readable text format
		Returns: Formatted string with company information
		"""
		from datetime import datetime
		
		# Get all relevant fields dynamically
		info_lines = []
		info_lines.append("=" * 60)
		info_lines.append("COMPANY INFORMATION")
		info_lines.append("=" * 60)
		info_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
		info_lines.append("")
		
		# Basic Information Section
		info_lines.append("BASIC INFORMATION")
		info_lines.append("-" * 60)
		info_lines.append(f"Employer Name: {self.employer_name or 'N/A'}")
		info_lines.append(f"Company Registration Number: {self.company_reg_no or 'N/A'}")
		info_lines.append(f"Employer Code: {self.employer_code or 'N/A'}")
		info_lines.append(f"Status: {self.status or 'N/A'}")
		info_lines.append(f"City: {self.city or 'N/A'}")
		info_lines.append(f"Country: {self.country or 'N/A'}")
		info_lines.append(f"Address: {self.address or 'N/A'}")
		info_lines.append(f"Website: {self.website or 'N/A'}")
		info_lines.append("")
		
		# Primary Contact Section
		info_lines.append("PRIMARY CONTACT")
		info_lines.append("-" * 60)
		info_lines.append(f"Contact Name: {self.primary_contact_name or 'N/A'}")
		info_lines.append(f"Designation: {self.primary_contact_designation or 'N/A'}")
		info_lines.append(f"Phone: {self.primary_contact_phone or 'N/A'}")
		info_lines.append(f"Email: {self.primary_contact_email or 'N/A'}")
		info_lines.append("")
		
		# Recruitment Configuration Section
		info_lines.append("RECRUITMENT CONFIGURATION")
		info_lines.append("-" * 60)
		info_lines.append(f"Preferred Language: {self.preferred_language or 'N/A'}")
		info_lines.append(f"Recruitment Active: {'Yes' if self.recruitment_active else 'No'}")
		info_lines.append(f"Default Currency: {self.default_currency or 'N/A'}")
		info_lines.append("")
		
		# Legal Summary Section
		info_lines.append("LEGAL SUMMARY")
		info_lines.append("-" * 60)
		info_lines.append(f"POA Valid Till: {self.poa_valid_till or 'N/A'}")
		info_lines.append(f"MOU Available: {'Yes' if self.mou_available else 'No'}")
		info_lines.append(f"Have POA: {'Yes' if self.have_poa else 'No'}")
		info_lines.append("")
		
		# Additional Information
		if self.internal_notes:
			info_lines.append("INTERNAL NOTES")
			info_lines.append("-" * 60)
			info_lines.append(self.internal_notes)
			info_lines.append("")
		
		if self.remarks:
			info_lines.append("REMARKS")
			info_lines.append("-" * 60)
			info_lines.append(self.remarks)
			info_lines.append("")
		
		info_lines.append("=" * 60)
		info_lines.append(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
		info_lines.append("=" * 60)
		
		return "\n".join(info_lines)
	
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
			from drive.utils import create_drive_file
			from drive.utils.files import FileManager
			from drive.utils import get_home_folder
			from pathlib import Path
			
			# Get home folder
			home_folder = get_home_folder(team)
			if not home_folder:
				return
			
			# Get parent folder document
			parent_doc = frappe.get_doc("Drive File", parent_folder)
			
			# Create file path using FileManager
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
			
			# Create Drive File document
			drive_file = create_drive_file(
				team=team,
				title=file_name,
				parent=parent_folder,
				mime_type="text/plain",
				entity_path=lambda _: file_path,
				is_group=False,
			)
			
		except Exception as e:
			frappe.log_error(
				f"Error creating Drive text file {file_name}: {str(e)}\n{frappe.get_traceback()}",
				"Drive Text File Creation Error"
			)
	
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
			
		except Exception as e:
			frappe.log_error(
				f"Error updating Drive file content {drive_file_name}: {str(e)}\n{frappe.get_traceback()}",
				"Drive File Update Error"
			)
	
	@frappe.whitelist()
	def create_drive_folders(self):
		"""
		Function: create_drive_folders
		Purpose: Whitelisted method to manually create Drive folders for an Employer
		Operation: Calls create_employer_drive_structure() to set up all folders
		Returns: Dictionary with success status and message
		"""
		if not self.employer_name:
			return {
				"success": False,
				"message": _("Employer name is required to create Drive folders")
			}
		
		try:
			result = self.create_employer_drive_structure()
			if result:
				return {
					"success": True,
					"message": _("Drive folders created successfully for {0}").format(self.employer_name)
				}
			else:
				return {
					"success": False,
					"message": _("Failed to create Drive folders. Please check Error Log for details.")
				}
		except Exception as e:
			frappe.log_error(
				f"Error creating Drive folders for Employer {self.name}: {str(e)}\n{frappe.get_traceback()}",
				"Employer Drive Folder Creation Error"
			)
			return {
				"success": False,
				"message": _("Error creating Drive folders: {0}").format(str(e))
			}
	
	@frappe.whitelist()
	def diagnose_drive_folder_issue(self):
		"""
		Function: diagnose_drive_folder_issue
		Purpose: Diagnostic method to check why folder creation might be failing
		Returns: Dictionary with diagnostic information
		"""
		diagnostics = {
			"employer_name": self.employer_name,
			"employer_id": self.name,
			"issues": [],
			"info": {}
		}
		
		try:
			# Check 1: Employer name
			if not self.employer_name:
				diagnostics["issues"].append("Employer name is missing")
				return diagnostics
			
			# Check 2: Drive app installed
			if not frappe.db.exists("DocType", "Drive File"):
				diagnostics["issues"].append("Drive app is not installed")
				return diagnostics
			
			# Check 3: Drive team
			team = self.get_drive_team()
			if not team:
				diagnostics["issues"].append(f"No Drive team found for user {frappe.session.user}")
				return diagnostics
			diagnostics["info"]["team"] = team
			
			# Check 4: Home folder
			home_folder = self.get_home_folder(team)
			if not home_folder:
				diagnostics["issues"].append(f"Home folder not found for team {team}")
				return diagnostics
			diagnostics["info"]["home_folder"] = home_folder
			
			# Check 5: Employers root folder
			employers_root = self.get_drive_folder_by_title("Employers", home_folder, team)
			if not employers_root:
				diagnostics["issues"].append("Employers root folder does not exist")
				return diagnostics
			diagnostics["info"]["employers_root"] = employers_root
			
			# Check 6: Permissions on Employers root
			try:
				from drive.api.permissions import user_has_permission
				root_doc = frappe.get_doc("Drive File", employers_root)
				has_upload = user_has_permission(root_doc, "upload")
				diagnostics["info"]["has_upload_permission"] = has_upload
				if not has_upload:
					diagnostics["issues"].append(f"User {frappe.session.user} does not have upload permission on Employers root folder")
			except Exception as perm_error:
				diagnostics["issues"].append(f"Error checking permissions: {str(perm_error)}")
			
			# Check 7: Check if folder already exists
			folder_name = self.sanitize_folder_name(self.employer_name)
			existing_folder = self.get_drive_folder_by_title(folder_name, employers_root, team)
			diagnostics["info"]["folder_name"] = folder_name
			diagnostics["info"]["existing_folder"] = existing_folder
			
			if existing_folder:
				diagnostics["info"]["status"] = "Folder already exists"
			else:
				diagnostics["info"]["status"] = "Folder does not exist - should be created"
			
		except Exception as e:
			diagnostics["issues"].append(f"Error during diagnosis: {str(e)}")
			diagnostics["error_traceback"] = frappe.get_traceback()
		
		return diagnostics
	
	@frappe.whitelist()
	def reprocess_document_files(self):
		"""
		Function: reprocess_document_files
		Purpose: Whitelisted method to reprocess all Employer Document files and move them to Drive
		Operation: Processes all documents in the child table and moves files to correct Drive folders
		Returns: Dictionary with success status and message
		"""
		if not self.employer_name:
			return {
				"success": False,
				"message": _("Employer name is required")
			}
		
		try:
			# Process all document files
			self.process_employer_document_files()
			
			# Count how many documents were processed
			saved_documents = frappe.get_all(
				"Employer Document",
				filters={"parent": self.name, "parenttype": "Employer"},
				fields=["name", "document_file", "document_type"]
			)
			
			processed_count = sum(1 for doc in saved_documents if doc.get("document_file") and doc.get("document_type"))
			
			return {
				"success": True,
				"message": _("Processed {0} document(s). Files should now be in Drive folders.").format(processed_count)
			}
		except Exception as e:
			frappe.log_error(
				f"Error reprocessing document files for Employer {self.name}: {str(e)}\n{frappe.get_traceback()}",
				"Employer Document File Reprocessing Error"
			)
			return {
				"success": False,
				"message": _("Error reprocessing files: {0}").format(str(e))
			}
	
	@frappe.whitelist()
	def recreate_drive_folders(self):
		"""
		Function: recreate_drive_folders
		Purpose: Whitelisted method to recreate Drive folders for an Employer (useful if folders were deleted)
		Operation: Deletes existing folder structure (if exists) and creates fresh folders
		Returns: Dictionary with success status and message
		"""
		if not self.employer_name:
			return {
				"success": False,
				"message": _("Employer name is required to recreate Drive folders")
			}
		
		try:
			# Try to delete existing folder structure first (if exists)
			try:
				self.delete_employer_drive_folders()
			except Exception:
				# Ignore errors if folder doesn't exist
				pass
			
			# Create fresh folder structure
			result = self.create_employer_drive_structure()
			if result:
				return {
					"success": True,
					"message": _("Drive folders recreated successfully for {0}").format(self.employer_name)
				}
			else:
				return {
					"success": False,
					"message": _("Failed to recreate Drive folders. Please check Error Log for details.")
				}
		except Exception as e:
			frappe.log_error(
				f"Error recreating Drive folders for Employer {self.name}: {str(e)}\n{frappe.get_traceback()}",
				"Employer Drive Folder Recreation Error"
			)
			return {
				"success": False,
				"message": _("Error recreating Drive folders: {0}").format(str(e))
			}
