# Copyright (c) 2026, abdullahjavaid198@gmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
import re


class Applicant(Document):
	def validate(self):
		"""
		Function: validate
		Purpose: Main validation method called by Frappe framework before saving the document
		Operation: Executes all validation methods in the correct order:
			1. Format validation (CNIC and Passport)
			2. Uniqueness validation (CNIC and Passport)
			3. Age calculation from date of birth
			4. Document completeness validation
		"""
		self.validate_cnic_format()
		self.validate_passport_format()
		self.validate_unique_cnic()
		self.validate_unique_passport_number()
		self.calculate_age_from_dob()
		self.validate_documents_completeness()
	
	def validate_cnic_format(self):
		"""
		Function: validate_cnic_format
		Purpose: Validates that CNIC follows the required format: exactly 13 digits without dashes
		Operation: 
			- Removes dashes and spaces from CNIC
			- Checks if the cleaned CNIC contains exactly 13 digits
			- Throws validation error if format is invalid
			- Updates CNIC field with cleaned value (without dashes)
		Trigger: Called during document validation before save
		"""
		if not self.cnic:
			return
		
		import re
		
		# Remove dashes and spaces
		cleaned_cnic = re.sub(r'[-\s]', '', str(self.cnic))
		
		# Check if it's exactly 13 digits
		if not re.match(r'^\d{13}$', cleaned_cnic):
			frappe.throw(
				_("CNIC must be exactly 13 digits without dashes."),
				title=_("Invalid CNIC Format")
			)
		
		# Update with cleaned value (without dashes)
		if self.cnic != cleaned_cnic:
			self.cnic = cleaned_cnic
	
	def validate_passport_format(self):
		"""
		Function: validate_passport_format
		Purpose: Validates that Passport Number follows the required format: 2 letters followed by 7 digits
		Operation:
			- Converts passport number to uppercase and strips whitespace
			- Checks if format matches: 2 uppercase letters + 7 digits (total 9 characters)
			- Throws validation error if format is invalid
			- Updates passport_number field with uppercase value
		Trigger: Called during document validation before save
		"""
		if not self.passport_number:
			return
		
		import re
		
		passport = str(self.passport_number).strip().upper()
		
		# Check format: 2 letters followed by 7 digits (total 9 characters)
		if not re.match(r'^[A-Z]{2}\d{7}$', passport):
			frappe.throw(
				_("Passport Number must be in format: 2 letters followed by 7 digits (e.g., AB1234567)."),
				title=_("Invalid Passport Format")
			)
		
		# Update with uppercase value
		if self.passport_number != passport:
			self.passport_number = passport
	
	def validate_unique_cnic(self):
		"""
		Function: validate_unique_cnic
		Purpose: Validates that CNIC is unique across all Applicant records in the system
		Operation:
			- Checks database for existing Applicant with same CNIC
			- Excludes current document from the check (for updates)
			- Throws DuplicateEntryError if CNIC already exists
		Trigger: Called during document validation before save
		"""
		if not self.cnic:
			return
		
		existing = frappe.db.exists(
			"Applicant",
			{
				"cnic": self.cnic,
				"name": ["!=", self.name]
			}
		)
		
		if existing:
			frappe.throw( 
				_("Applicant with CNIC {0} already exists.").format(self.cnic),
				frappe.DuplicateEntryError
			)
	
	def validate_unique_passport_number(self):
		"""
		Function: validate_unique_passport_number
		Purpose: Validates that Passport Number is unique across all Applicant records in the system
		Operation:
			- Checks database for existing Applicant with same passport_number
			- Excludes current document from the check (for updates)
			- Throws DuplicateEntryError if passport_number already exists
		Trigger: Called during document validation before save
		"""
		if not self.passport_number:
			return
		
		existing = frappe.db.exists(
			"Applicant",
			{
				"passport_number": self.passport_number,
				"name": ["!=", self.name]
			}
		)
		
		if existing:
			frappe.throw(
				_("Applicant with Passport Number {0} already exists.").format(self.passport_number),
				frappe.DuplicateEntryError
			)
	
	def calculate_age_from_dob(self):
		"""
		Function: calculate_age_from_dob
		Purpose: Calculates and updates the age field based on date_of_birth
		Operation:
			- Calculates the difference between current date and date of birth
			- Adjusts age if birthday hasn't occurred this year
			- Sets age to None if date_of_birth is not provided
		Trigger: Called during document validation before save
		"""
		if self.date_of_birth:
			from frappe.utils import getdate, today
			
			birth_date = getdate(self.date_of_birth)
			current_date = getdate(today())
			
			# Calculate age
			age = current_date.year - birth_date.year
			
			# Adjust if birthday hasn't occurred this year
			if (current_date.month, current_date.day) < (birth_date.month, birth_date.day):
				age -= 1
			
			self.age = age
		else:
			self.age = None
	
	def validate_documents_completeness(self):
		"""
		Function: validate_documents_completeness
		Purpose: Check if all documents in applicant_document child table have files uploaded
		Operation:
			- Checks each row in applicant_document child table
			- Identifies documents without files
			- Auto-sets is_missing_documents flag if documents are missing
			- Auto-populates missing_documents_name field if checkbox is checked and field is empty
		Trigger: Called during document validation before save
		"""
		# Check if custom fields exist
		if not frappe.db.has_column("Applicant", "is_missing_documents"):
			return
		
		# Get all document types that should have files but don't
		documents_without_files = []
		
		if hasattr(self, 'applicant_document') and self.applicant_document:
			for doc_row in self.applicant_document:
				# Check if document_type is set but file is missing
				if doc_row.document_type and not doc_row.file:
					documents_without_files.append(doc_row.document_type)
		
		# Auto-set is_missing_documents flag if documents are missing
		if documents_without_files:
			# Set the checkbox if not already set
			if hasattr(self, 'is_missing_documents') and not self.is_missing_documents:  
				self.is_missing_documents = 1
			
			# Auto-populate missing_documents_name field if checkbox is checked and field is empty
			if hasattr(self, 'missing_documents_name') and self.is_missing_documents:
				current_missing = (self.missing_documents_name or "").strip()
				if not current_missing:
					# Create a comma-separated list of missing documents
					missing_list = ", ".join(documents_without_files)
					self.missing_documents_name = missing_list
		else:
			# All documents have files
			# Only auto-uncheck if we haven't manually set it (preserve user intent)
			# We'll leave the checkbox state as is to allow manual override
			pass
	
	def get_missing_documents_list(self):
		"""
		Function: get_missing_documents_list
		Purpose: Get a list of document types that are missing files
		Returns: List of document type strings
		"""
		missing = []
		
		if hasattr(self, 'applicant_document') and self.applicant_document:
			for doc_row in self.applicant_document:
				if doc_row.document_type and not doc_row.file:
					missing.append(doc_row.document_type)
		
		return missing
	
	@frappe.whitelist()
	def check_documents_status(self):
		"""
		Whitelisted method to check document status and return missing documents
		Returns: Dictionary with status and missing documents list
		"""
		missing = self.get_missing_documents_list()
		
		return {
			"has_missing_documents": len(missing) > 0,
			"missing_documents": missing,
			"missing_count": len(missing),
			"total_documents": len(self.applicant_document) if hasattr(self, 'applicant_document') and self.applicant_document else 0
		}
	
	def after_insert(self):
		"""
		Function: after_insert
		Purpose: Automatically create Drive folder structure when a new Applicant is created
		Operation:
			- Creates main Applicant folder: /Applicants/{Full Name} - {CNIC}/
			- Creates all required subfolders (CV, Passport, CNIC, Education, etc.)
			- Uses CNIC as the unique identifier for folder lookup
			- Idempotent: won't create duplicates if folders already exist
		Trigger: Called automatically after document is inserted into database
		"""
		self.create_applicant_drive_folders()
	
	def on_update(self):
		"""
		Function: on_update
		Purpose: Handle file uploads from Applicant Document child table after parent is saved
		Operation:
			- Ensures folder structure exists (creates if missing)
			- Processes all files in applicant_document child table
			- Moves files to correct Drive subfolders
			- This runs after child table rows are saved, ensuring File documents are created
		Trigger: Called automatically when document is updated
		"""
		# Ensure folder structure exists (in case it wasn't created on insert)
		if self.cnic and self.full_name:
			self.create_applicant_drive_folders()
		
		# Process files from child table
		self.process_applicant_document_files()
	
	def on_trash(self):
		"""
		Function: on_trash
		Purpose: Delete entire Applicant Drive folder structure when Applicant is deleted
		Operation:
			- Finds the Applicant's main folder using CNIC
			- Recursively deletes all subfolders and files
			- Ensures no orphan files/folders remain
		Trigger: Called automatically before document is deleted from database
		"""
		self.delete_applicant_drive_folders()
	
	def create_applicant_drive_folders(self):
		"""
		Function: create_applicant_drive_folders
		Purpose: Create the complete Drive folder structure for an Applicant using Frappe Drive
		Operation:
			1. Get user's default Drive team
			2. Get home folder for the team
			3. Create /Applicants/ root folder (if not exists)
			4. Create individual Applicant folder: {Full Name} - {CNIC}
			5. Create all required subfolders
		Returns: True if successful, False otherwise
		"""
		if not self.cnic or not self.full_name:
			# Don't log error if fields are just not filled yet (during form editing)
			return False
		
		try:
			# Get user's default Drive team
			team = self.get_drive_team()
			if not team:
				frappe.log_error(
					f"No Drive team found for user {frappe.session.user}. Please create a Drive Team first.",
					"Applicant Drive Folder Creation Error"
				)
				return False
			
			# Get home folder for the team
			home_folder = self.get_home_folder(team)
			if not home_folder:
				frappe.log_error(
					f"Home folder not found for team {team}",
					"Applicant Drive Folder Creation Error"
				)
				return False
			
			# Sanitize full_name for folder naming
			sanitized_name = self.sanitize_folder_name(self.full_name)
			folder_name = f"{sanitized_name} - {self.cnic}"
			
			# Ensure folder name doesn't exceed limit (140 chars)
			if len(folder_name) > 140:
				# Truncate name part, keep CNIC
				max_name_length = 140 - len(f" - {self.cnic}")
				sanitized_name = sanitized_name[:max_name_length] if max_name_length > 0 else ""
				folder_name = f"{sanitized_name} - {self.cnic}"
			
			# Step 1: Get or create main /Applicants/ root folder
			applicants_root = self.get_or_create_drive_folder("Applicants", home_folder, team)
			if not applicants_root:
				return False
			
			# Step 2: Get or create individual Applicant folder inside /Applicants/
			applicant_folder = self.get_or_create_drive_folder(folder_name, applicants_root, team)
			if not applicant_folder:
				return False
			
			# Step 3: Create all required subfolders
			# Create a folder for each document type in the dropdown
			subfolders = [
				"CV",
				"Passport",
				"CNIC",
				"License",
				"Certificate",
				"Medical",
				"Education",
				"Experience",
				"Police",
				"Visa",
				"Work Permit",
				"Bank Statement",
				"Salary Certificate",
				"Reference Letter",
				"Contract",
				"Other"
			]
			
			for subfolder_name in subfolders:
				self.get_or_create_drive_folder(subfolder_name, applicant_folder, team)
			
			# Only show message if not in import/API mode and not in background
			if not frappe.flags.in_import and not frappe.flags.in_migrate and not frappe.flags.in_install:
				# Use frappe.publish_realtime for non-blocking message
				frappe.publish_realtime(
					"drive_folders_created",
					{"message": _("Drive folders created successfully")},
					user=frappe.session.user
				)
			
			return True
			
		except Exception as e:
			frappe.log_error(
				f"Error creating Drive folders for Applicant {self.name} (CNIC: {self.cnic}): {str(e)}\n{frappe.get_traceback()}",
				"Applicant Drive Folder Creation Error"
			)
			# Don't throw error - allow Applicant creation to succeed even if folder creation fails
			return False
	
	def delete_applicant_drive_folders(self):
		"""
		Function: delete_applicant_drive_folders
		Purpose: Delete the entire Drive folder structure for an Applicant
		Operation:
			1. Find the Applicant's main folder using CNIC
			2. Recursively delete all files and subfolders
			3. Delete the main folder itself
		"""
		if not self.cnic:
			return
		
		try:
			team = self.get_drive_team()
			if not team:
				return
			
			home_folder = self.get_home_folder(team)
			if not home_folder:
				return
			
			# Find Applicants root folder
			applicants_root = self.get_drive_folder_by_title("Applicants", home_folder, team)
			if not applicants_root:
				return
			
			# Find Applicant folder by CNIC
			sanitized_name = self.sanitize_folder_name(self.full_name) if self.full_name else ""
			folder_name = f"{sanitized_name} - {self.cnic}"
			
			applicant_folder = self.get_drive_folder_by_title(folder_name, applicants_root, team)
			if applicant_folder:
				# Recursively delete the folder
				self.delete_drive_folder_recursive(applicant_folder)
				
		except Exception as e:
			frappe.log_error(
				f"Error deleting Drive folders for Applicant {self.name}: {str(e)}",
				"Applicant Drive Folder Deletion Error"
			)
	
	def get_drive_team(self):
		"""
		Function: get_drive_team
		Purpose: Get the user's default Drive team
		Returns: Team name (string) or None
		"""
		try:
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
		except Exception:
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
		Returns: Drive File document name (string)
		"""
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
		
		# Create new folder
		try:
			from pathlib import Path
			from drive.utils import create_drive_file
			from drive.utils.files import FileManager
			from drive.utils import get_home_folder
			
			# Get parent folder document
			parent_doc = frappe.get_doc("Drive File", parent_entity)
			home_folder = get_home_folder(team)
			
			# Create folder path using FileManager
			manager = FileManager()
			path = manager.create_folder(
				frappe._dict({
					"title": title,
					"team": team,
					"parent_path": Path(parent_doc.path or ""),
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
			
			return drive_file.name
			
		except Exception as e:
			error_str = str(e).lower()
			
			# Handle "File exists" error gracefully (idempotent)
			if "file exists" in error_str or "errno 17" in error_str or "already exists" in error_str:
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
			
			# Log error but don't fail - allow Applicant creation to succeed
			frappe.log_error(
				f"Error creating Drive folder '{title}': {str(e)}\n{frappe.get_traceback()}",
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
				folder_doc.delete()
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
				f"Error deleting Drive folder {folder_name}: {str(e)}",
				"Drive Folder Deletion Error"
			)
	
	def sanitize_folder_name(self, name):
		"""
		Function: sanitize_folder_name
		Purpose: Sanitize folder name by removing invalid characters and ensuring length limits
		Operation:
			- Removes slashes, backslashes
			- Removes extra spaces
			- Trims whitespace
			- Truncates to 140 characters (Drive limit)
		Returns: Sanitized folder name string
		"""
		if not name:
			return ""
		
		# Remove slashes and backslashes
		sanitized = re.sub(r'[/\\]', '', str(name))
		
		# Replace multiple spaces with single space
		sanitized = re.sub(r'\s+', ' ', sanitized)
		
		# Trim whitespace
		sanitized = sanitized.strip()
		
		# Truncate to 140 characters (Drive folder name limit)
		if len(sanitized) > 140:
			sanitized = sanitized[:137] + "..."
		
		return sanitized
	
	def get_applicant_drive_folder(self):
		"""
		Function: get_applicant_drive_folder
		Purpose: Get the main Drive folder for this Applicant
		Returns: Drive File document name (string) or None
		"""
		if not self.cnic:
			return None
		
		try:
			team = self.get_drive_team()
			if not team:
				return None
			
			home_folder = self.get_home_folder(team)
			if not home_folder:
				return None
			
			# Get Applicants root folder
			applicants_root = self.get_drive_folder_by_title("Applicants", home_folder, team)
			if not applicants_root:
				return None
			
			# Find folder ending with this CNIC
			sanitized_name = self.sanitize_folder_name(self.full_name) if self.full_name else ""
			folder_name = f"{sanitized_name} - {self.cnic}"
			
			return self.get_drive_folder_by_title(folder_name, applicants_root, team)
			
		except Exception as e:
			frappe.log_error(
				f"Error getting Drive folder for Applicant {self.name}: {str(e)}",
				"Applicant Drive Folder Lookup Error"
			)
			return None
	
	def get_document_subfolder(self, document_type):
		"""
		Function: get_document_subfolder
		Purpose: Get the appropriate subfolder name for a document type
		Operation:
			- Maps each document type to its corresponding Drive subfolder
			- Handles all document types from the dropdown
			- Returns default "Certificates" for unmapped types
		Parameters:
			- document_type: Document type string from dropdown
		Returns: Subfolder name string (never None)
		"""
		if not document_type:
			return "Certificates"
		
		# Normalize document_type (strip whitespace, handle case)
		document_type = str(document_type).strip()
		
		# Complete mapping of all document types to Drive folders
		# Each document type maps to its own folder (1:1 mapping)
		mapping = {
			"CV": "CV",
			"Passport": "Passport",
			"CNIC": "CNIC",
			"License": "License",
			"Certificate": "Certificate",
			"Medical": "Medical",
			"Education": "Education",
			"Experience": "Experience",
			"Police": "Police",
			"Visa": "Visa",
			"Work Permit": "Work Permit",
			"Bank Statement": "Bank Statement",
			"Salary Certificate": "Salary Certificate",
			"Reference Letter": "Reference Letter",
			"Contract": "Contract",
			"Other": "Other"
		}
		
		# Get mapped folder name, default to document_type itself if not mapped
		# This ensures every document type gets its own folder
		subfolder = mapping.get(document_type, document_type)
		
		# Log if document type is not in mapping (for debugging)
		if document_type not in mapping:
			frappe.log_error(
				f"Document type '{document_type}' not in mapping, using default 'Certificates'",
				"Document Type Mapping Warning"
			)
		
		return subfolder
	
	def process_applicant_document_files(self):
		"""
		Function: process_applicant_document_files
		Purpose: Process all files in applicant_document child table and move them to Drive folders
		Operation:
			- Gets all saved applicant_document rows from database
			- For each row with a file, moves it to the correct Drive subfolder
			- This ensures files are processed after the parent document is saved
			- Handles files added before or after parent save
		"""
		# Ensure Applicant is saved before processing files
		if not self.name or not frappe.db.exists("Applicant", self.name):
			return
		
		team = self.get_drive_team()
		if not team:
			return
		
		# Ensure folder structure exists
		if not self.create_applicant_drive_folders():
			# Folder creation failed, but continue to try processing files
			pass
		
		# Get Applicant's main folder
		applicant_folder_name = self.get_applicant_drive_folder()
		if not applicant_folder_name:
			return
		
		# Get all saved applicant_document rows from database (not just form)
		saved_documents = frappe.get_all(
			"Applicant Document",
			filters={"parent": self.name, "parenttype": "Applicant"},
			fields=["name", "file", "document_type"]
		)
		
		# Process each document from database
		for doc_data in saved_documents:
			if not doc_data.get("file") or not doc_data.get("document_type"):
				continue
			
			try:
				# Get subfolder name for this document type
				document_type = doc_data.get("document_type")
				if not document_type:
					continue
				
				subfolder_name = self.get_document_subfolder(document_type)
				if not subfolder_name or not subfolder_name.strip():
					frappe.log_error(
						f"Invalid subfolder name for document type: {document_type}",
						"Applicant Document File Processing Error"
					)
					continue
				
				# Get or create subfolder
				subfolder_drive = self.get_or_create_drive_folder(subfolder_name, applicant_folder_name, team)
				if not subfolder_drive:
					continue
				
				# Find the File document
				file_doc = self.find_file_document_by_url(doc_data.get("file"))
				if not file_doc:
					continue
				
				# Create or move Drive File entry
				self.create_or_move_drive_file_for_row(file_doc, subfolder_drive, team)
				
			except Exception as e:
				frappe.log_error(
					f"Error processing file for Applicant Document {doc_data.get('name')}: {str(e)}\n{frappe.get_traceback()}",
					"Applicant Document File Processing Error"
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
		
		# Method 3: Lookup by attached_to (files attached to parent Applicant)
		if not file_name and self.name:
			file_name = frappe.db.get_value(
				"File",
				{
					"attached_to_name": self.name,
					"attached_to_doctype": "Applicant",
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
	
	def find_file_document_for_row(self, doc_row):
		"""
		Function: find_file_document_for_row
		Purpose: Find the File document for a child table row
		Parameters:
			- doc_row: Applicant Document child table row
		Returns: File document or None
		"""
		if not doc_row.file:
			return None
		
		# Method 1: Lookup by file_url (exact match)
		file_name = frappe.db.get_value("File", {"file_url": doc_row.file}, "name")
		
		# Method 2: Extract filename from URL and lookup
		if not file_name:
			file_url_clean = doc_row.file
			if "/files/" in file_url_clean:
				file_url_clean = file_url_clean.split("/files/")[-1]
			if "/private/files/" in file_url_clean:
				file_url_clean = file_url_clean.split("/private/files/")[-1]
			file_name_from_url = file_url_clean.split("/")[-1].split("?")[0]
			file_name = frappe.db.get_value("File", {"file_name": file_name_from_url}, "name")
		
		# Method 3: Lookup by attached_to (files attached to parent Applicant)
		if not file_name:
			file_name = frappe.db.get_value(
				"File",
				{
					"attached_to_name": self.name,
					"attached_to_doctype": "Applicant",
					"file_url": doc_row.file
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
			- file_doc: File document
			- parent_folder: Drive File folder name (parent_entity)
			- team: Drive team name
		"""
		# Check if Drive File already exists in the correct location
		existing_drive_file = frappe.db.get_value(
			"Drive File",
			{
				"title": file_doc.file_name,
				"parent_entity": parent_folder,
				"team": team,
				"is_active": 1
			},
			"name"
		)
		
		if existing_drive_file:
			# Already exists in the correct location
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
				if drive_file_doc.parent_entity != parent_folder:
					drive_file_doc.move(new_parent=parent_folder)
			except Exception as e:
				frappe.log_error(
					f"Error moving Drive File {existing_drive_file_anywhere}: {str(e)}",
					"Drive File Move Error"
				)
			return
		
		# Create new Drive File entry from File document
		try:
			from pathlib import Path
			from drive.utils import create_drive_file, get_home_folder
			from drive.utils.files import FileManager
			import os
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
			
			# Create Drive File
			manager = FileManager()
			drive_file = create_drive_file(
				team=team,
				title=file_doc.file_name,
				parent=parent_folder,
				mime_type=mime_type,
				entity_path=lambda entity: manager.get_disk_path(entity, home_folder, embed=0),
				file_size=file_size,
			)
			
			# Copy/move file to Drive location
			if file_path.exists():
				manager.upload_file(file_path, drive_file, create_thumbnail=True)
			
		except Exception as e:
			frappe.log_error(
				f"Error creating Drive File for {file_doc.name}: {str(e)}\n{frappe.get_traceback()}",
				"Drive File Creation Error"
			)