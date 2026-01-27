# Copyright (c) 2026, abdullahjavaid198@gmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EmployerDocument(Document):
	def after_insert(self):
		"""
		Function: after_insert
		Purpose: Handle file upload when a new document is added to Employer Document child table
		Operation:
			- Only processes if parent Employer is already saved (exists in database)
			- If parent doesn't exist yet, file processing will happen in parent's on_update hook
		Trigger: Called automatically after document is inserted into database
		"""
		# Only process if parent exists in database (already saved)
		if self.document_file and self.parent and frappe.db.exists("Employer", self.parent):
			self.handle_file_upload()
	
	def on_update(self):
		"""
		Function: on_update
		Purpose: Handle file replacement when document is updated
		Operation:
			- Detects if file has changed
			- Deletes old file from Drive
			- Moves new file to correct subfolder
		Trigger: Called automatically when document is updated
		"""
		# Check if file has changed
		if self.has_value_changed("document_file"):
			old_file = self.get_doc_before_save().document_file if self.get_doc_before_save() else None
			new_file = self.document_file
			
			# Delete old file from Drive if it exists
			if old_file:
				# Use old document_type if available, otherwise current
				old_doc = self.get_doc_before_save()
				old_document_type = old_doc.get("document_type") if old_doc else self.document_type
				self.delete_drive_file(old_file, old_document_type, self.parent)
			
			# Handle new file upload
			if new_file:
				self.handle_file_upload()
	
	def before_delete(self):
		"""
		Function: before_delete
		Purpose: Store file and document_type before deletion (data might not be available in on_trash)
		Operation: Stores document_file URL and document_type in flags for use in on_trash
		Trigger: Called automatically before document is deleted from database
		"""
		# Store data in flags so it's available in on_trash
		self.flags.file_to_delete = self.document_file
		self.flags.document_type_to_delete = self.document_type
		self.flags.parent_to_delete = self.parent
	
	def on_trash(self):
		"""
		Function: on_trash
		Purpose: Delete Drive file when document row is deleted
		Operation:
			- Finds the Drive file in the correct subfolder based on document_type
			- Deletes the file from Drive (soft delete - marks as inactive)
			- Does not delete the Employer folder or other documents
		Trigger: Called automatically before document is deleted from database
		"""
		# Get file and document_type from flags (set in before_delete) or from self
		file_url = getattr(self.flags, 'file_to_delete', None) or (hasattr(self, 'document_file') and self.document_file)
		document_type = getattr(self.flags, 'document_type_to_delete', None) or (hasattr(self, 'document_type') and self.document_type)
		parent_name = getattr(self.flags, 'parent_to_delete', None) or (hasattr(self, 'parent') and self.parent)
		
		if file_url:
			# Always try to delete, even if document_type is missing (will search all folders)
			try:
				self.delete_drive_file(file_url, document_type, parent_name)
			except Exception as e:
				# Log error but don't prevent deletion
				frappe.log_error(
					f"Error in delete_drive_file for Employer Document: {str(e)}\nFile URL: {file_url}\nDocument Type: {document_type}\n{frappe.get_traceback()}",
					"Drive File Deletion Error"
				)
		else:
			doc_name = getattr(self, 'name', 'unknown')
			frappe.log_error(
				f"No file URL found for Employer Document {doc_name} during deletion",
				"Drive File Deletion Warning"
			)
	
	def handle_file_upload(self):
		"""
		Function: handle_file_upload
		Purpose: Move uploaded file to the correct Employer Drive subfolder
		Operation:
			1. Get parent Employer document
			2. Ensure Employer folder structure exists
			3. Get correct subfolder based on document_type (Legal/MOU, Legal/POA, etc.)
			4. Create Drive File entry in the correct subfolder
		"""
		if not self.document_file or not self.document_type:
			return
		
		try:
			# Get parent Employer document
			employer = self.get_parent_doc()
			if not employer:
				frappe.log_error(
					f"Cannot find parent Employer for Employer Document {self.name}",
					"Employer Document File Upload Error"
				)
				return
			
			# Ensure Employer folder structure exists (in case it wasn't created on insert)
			employer.create_employer_drive_structure()
			
			# Get Employer's main folder
			employer_folder_name = employer.get_employer_drive_folder()
			if not employer_folder_name:
				frappe.log_error(
					f"Cannot find Drive folder for Employer {employer.name}",
					"Employer Document File Upload Error"
				)
				return
			
			# Get subfolder mapping for this document type
			subfolder_info = employer.get_document_subfolder(self.document_type)
			
			# Validate subfolder mapping
			if not subfolder_info:
				# Document type not mapped, use "Other" as default
				subfolder_info = (None, "Other")
			
			parent_folder_name, subfolder_name = subfolder_info
			
			# Get team
			team = employer.get_drive_team()
			if not team:
				frappe.log_error(
					"No Drive team found for file upload",
					"Employer Document File Upload Error"
				)
				return
			
			# Get or create subfolder
			if parent_folder_name:
				# Document type has a parent folder (e.g., Legal)
				parent_folder = employer.get_or_create_drive_folder(parent_folder_name, employer_folder_name, team)
				if not parent_folder:
					return
				# Get or create subfolder under parent (MOU, POA, Contracts, Licenses, NDA)
				subfolder_drive = employer.get_or_create_drive_folder(subfolder_name, parent_folder, team)
			else:
				# Document type is a direct subfolder (e.g., Commercial Registration, Demands, etc.)
				subfolder_drive = employer.get_or_create_drive_folder(subfolder_name, employer_folder_name, team)
			
			if not subfolder_drive:
				return
			
			# Find the File document
			file_doc = self.find_file_document()
			if not file_doc:
				frappe.log_error(
					f"Cannot find File document for {self.document_file}",
					"Employer Document File Upload Error"
				)
				return
			
			# Create or move Drive File entry
			self.create_or_move_drive_file(file_doc, subfolder_drive, team)
			
		except Exception as e:
			frappe.log_error(
				f"Error handling file upload for Employer Document {self.name}: {str(e)}\n{frappe.get_traceback()}",
				"Employer Document File Upload Error"
			)
			# Don't throw error - allow document save to succeed
	
	def find_file_document(self):
		"""
		Function: find_file_document
		Purpose: Find the File document from the file URL
		Returns: File document or None
		"""
		if not self.document_file:
			return None
		
		return self._find_file_document_by_url(self.document_file)
	
	def _find_file_document_by_url(self, file_url):
		"""
		Function: _find_file_document_by_url
		Purpose: Find File document by file URL (helper method)
		Parameters:
			- file_url: File URL string
		Returns: File document or None
		"""
		if not file_url:
			return None
		
		file_name = None
		
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
		if not file_name and self.parent:
			file_name = frappe.db.get_value(
				"File",
				{
					"attached_to_name": self.parent,
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
	
	def create_or_move_drive_file(self, file_doc, parent_folder, team):
		"""
		Function: create_or_move_drive_file
		Purpose: Create or move a Drive File entry for an uploaded file
		Parameters:
			- file_doc: Frappe File document
			- parent_folder: Parent Drive File document name (subfolder)
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
				"is_group": 0  # Only files, not folders
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
				f"Error creating/moving Drive file for File {file_doc.name}: {str(e)}\n{frappe.get_traceback()}",
				"Drive File Creation Error"
			)
	
	def delete_drive_file(self, file_url, document_type=None, parent_name=None):
		"""
		Function: delete_drive_file
		Purpose: Delete a Drive file when document is deleted or replaced
		Operation:
			- Finds the File document from file_url
			- Locates the Drive File entry in the specific subfolder based on document_type
			- Soft deletes the Drive File (marks as inactive)
		Parameters:
			- file_url: File URL
			- document_type: Document type to find the correct subfolder (optional but recommended)
			- parent_name: Parent Employer name (optional, helps with lookup)
		"""
		if not file_url:
			return
		
		try:
			# Find File document using the file_url
			file_doc = self._find_file_document_by_url(file_url)
			if not file_doc:
				frappe.log_error(
					f"Cannot find File document for URL: {file_url}",
					"Drive File Deletion Error"
				)
				return
			
			# Get parent Employer to find the correct folder structure
			# Use parent_name if provided (from before_delete), otherwise try to get from self
			employer = None
			if parent_name and frappe.db.exists("Employer", parent_name):
				try:
					employer = frappe.get_doc("Employer", parent_name)
				except (frappe.DoesNotExistError, frappe.ValidationError):
					employer = None
			else:
				employer = self.get_parent_doc()  # This will use self.parent
			
			drive_file_name = None
			if not employer:
				# If parent doesn't exist, try to find Drive File by title only (fallback)
				drive_file_name = frappe.db.get_value(
					"Drive File",
					{
						"title": file_doc.file_name,
						"is_active": 1,
						"is_group": 0
					},
					"name"
				)
			else:
				# Get Employer's main folder
				employer_folder = employer.get_employer_drive_folder()
				
				if not employer_folder:
					# Fallback: search by title only
					drive_file_name = frappe.db.get_value(
						"Drive File",
						{
							"title": file_doc.file_name,
							"is_active": 1,
							"is_group": 0
						},
						"name"
					)
				else:
					# Use document_type to find the specific subfolder
					if document_type:
						# Get the subfolder mapping for this document type
						subfolder_info = employer.get_document_subfolder(document_type)
						
						if not subfolder_info:
							# Default to "Other" if not mapped
							subfolder_info = (None, "Other")
						
						parent_folder_name, subfolder_name = subfolder_info
						team = employer.get_drive_team()
						
						if parent_folder_name:
							# Document type has a parent folder (e.g., Legal)
							parent_drive_folder = frappe.db.get_value(
								"Drive File",
								{
									"title": parent_folder_name,
									"parent_entity": employer_folder,
									"is_group": 1,
									"is_active": 1,
									"team": team
								},
								"name"
							)
							
							if parent_drive_folder:
								# Find the specific subfolder (MOU, POA, Contracts, Licenses, NDA)
								subfolder_drive = frappe.db.get_value(
									"Drive File",
									{
										"title": subfolder_name,
										"parent_entity": parent_drive_folder,
										"is_group": 1,
										"is_active": 1,
										"team": team
									},
									"name"
								)
							else:
								subfolder_drive = None
						else:
							# Document type is a direct subfolder (e.g., Commercial Registration, Demands, etc.)
							subfolder_drive = frappe.db.get_value(
								"Drive File",
								{
									"title": subfolder_name,
									"parent_entity": employer_folder,
									"is_group": 1,
									"is_active": 1,
									"team": team
								},
								"name"
							)
						
						if subfolder_drive:
							# Search in the specific subfolder first (most accurate)
							# Try exact file name match first
							drive_file_name = frappe.db.get_value(
								"Drive File",
								{
									"title": file_doc.file_name,
									"parent_entity": subfolder_drive,
									"is_active": 1,
									"is_group": 0,
									"team": team
								},
								"name"
							)
							
							# If not found, try searching by file name pattern (in case Drive renamed it)
							if not drive_file_name:
								# Get all files in the subfolder and match by name pattern
								all_files = frappe.get_all(
									"Drive File",
									filters={
										"parent_entity": subfolder_drive,
										"is_active": 1,
										"is_group": 0,
										"team": team
									},
									fields=["name", "title"]
								)
								
								# Try to find file by matching file name (case-insensitive, partial match)
								file_name_lower = file_doc.file_name.lower()
								for df in all_files:
									if df.get("title") and file_name_lower in df.get("title", "").lower():
										drive_file_name = df.get("name")
										break
					
					# If still not found, search in all subfolders
					if not drive_file_name and employer_folder:
						team = employer.get_drive_team()
						drive_file_name = self._search_drive_file_in_all_subfolders(
							file_doc.file_name, employer_folder, team
						)
			
			# If still not found, try one more comprehensive search
			if not drive_file_name and employer and employer_folder:
				team = employer.get_drive_team()
				drive_file_name = self._comprehensive_drive_file_search(
					file_doc, employer_folder, document_type, team
				)
			
			if drive_file_name:
				try:
					drive_file_doc = frappe.get_doc("Drive File", drive_file_name)
					# Soft delete (mark as inactive)
					drive_file_doc.is_active = 0
					drive_file_doc.save(ignore_permissions=True)
					
					# Log success with more details
					frappe.log_error(
						f"Successfully deleted Drive file '{file_doc.file_name}' (Drive File: {drive_file_name}) from folder '{document_type or 'unknown'}'",
						"Drive File Deletion Success"
					)
				except frappe.DoesNotExistError:
					# Already deleted, ignore
					pass
				except Exception as e:
					frappe.log_error(
						f"Error deleting Drive File document {drive_file_name}: {str(e)}\n{frappe.get_traceback()}",
						"Drive File Deletion Error"
					)
			else:
				# File not found in Drive, log detailed debugging info
				debug_info = {
					"file_name": file_doc.file_name,
					"file_url": file_url,
					"document_type": document_type,
					"parent": parent_name,
					"employer_folder": employer.get_employer_drive_folder() if employer else None
				}
				frappe.log_error(
					f"Drive file '{file_doc.file_name}' not found in Drive folders. Debug info: {debug_info}",
					"Drive File Not Found Warning"
				)
			
		except Exception as e:
			frappe.log_error(
				f"Error deleting Drive file {file_url}: {str(e)}\n{frappe.get_traceback()}",
				"Employer Document File Deletion Error"
			)
	
	def _search_drive_file_in_all_subfolders(self, file_name, employer_folder, team):
		"""
		Function: _search_drive_file_in_all_subfolders
		Purpose: Search for a file in all subfolders of an Employer (Legal and direct subfolders)
		Parameters:
			- file_name: File name to search for
			- employer_folder: Employer's main Drive folder name
			- team: Drive team name
		Returns: Drive File document name (string) or None
		"""
		try:
			# Get all direct subfolders (e.g., Commercial Registration, Demands, etc.)
			direct_subfolders = frappe.get_all(
				"Drive File",
				filters={
					"parent_entity": employer_folder,
					"is_group": 1,
					"is_active": 1,
					"team": team
				},
				fields=["name", "title"]
			)
			
			# Search in each direct subfolder
			for subfolder in direct_subfolders:
				drive_file_name = frappe.db.get_value(
					"Drive File",
					{
						"title": file_name,
						"parent_entity": subfolder.name,
						"is_active": 1,
						"is_group": 0,
						"team": team
					},
					"name"
				)
				
				if drive_file_name:
					return drive_file_name
				
				# If subfolder is "Legal", also search in its subfolders
				if subfolder.title == "Legal":
					legal_subfolders = frappe.get_all(
						"Drive File",
						filters={
							"parent_entity": subfolder.name,
							"is_group": 1,
							"is_active": 1,
							"team": team
						},
						fields=["name"]
					)
					
					# Search in each Legal subfolder
					for legal_subfolder in legal_subfolders:
						drive_file_name = frappe.db.get_value(
							"Drive File",
							{
								"title": file_name,
								"parent_entity": legal_subfolder.name,
								"is_active": 1,
								"is_group": 0,
								"team": team
							},
							"name"
						)
						
						if drive_file_name:
							return drive_file_name
			
			return None
			
		except Exception as e:
			frappe.log_error(
				f"Error searching for file in all subfolders: {str(e)}",
				"Drive File Search Error"
			)
			return None
	
	def _comprehensive_drive_file_search(self, file_doc, employer_folder, document_type, team):
		"""
		Function: _comprehensive_drive_file_search
		Purpose: Comprehensive search for Drive file by title, path, and content hash
		Parameters:
			- file_doc: Frappe File document
			- employer_folder: Employer's main Drive folder name
			- document_type: Document type (optional)
			- team: Drive team name
		Returns: Drive File document name (string) or None
		"""
		try:
			# Search by title within Employer folder (recursive search)
			all_files = frappe.get_all(
				"Drive File",
				filters={
					"is_active": 1,
					"is_group": 0,
					"team": team
				},
				fields=["name", "title", "parent_entity"]
			)
			
			# Check if file is within Employer folder structure
			file_name_lower = file_doc.file_name.lower()
			for df in all_files:
				if df.get("title") and file_name_lower in df.get("title", "").lower():
					# Check if this file is within the Employer folder structure
					parent_path = self._get_drive_file_path(df.get("parent_entity"), employer_folder)
					if parent_path:
						return df.get("name")
			
			return None
			
		except Exception as e:
			frappe.log_error(
				f"Error in comprehensive Drive file search: {str(e)}",
				"Drive File Search Error"
			)
			return None
	
	def _get_drive_file_path(self, drive_file_name, target_folder):
		"""
		Function: _get_drive_file_path
		Purpose: Check if a Drive file is within a target folder structure (recursive check)
		Parameters:
			- drive_file_name: Drive File document name to check
			- target_folder: Target folder name to check against
		Returns: True if file is within target folder, False otherwise
		"""
		try:
			current = drive_file_name
			max_depth = 10  # Prevent infinite loops
			depth = 0
			
			while current and depth < max_depth:
				try:
					drive_file_doc = frappe.get_doc("Drive File", current)
					if drive_file_doc.name == target_folder:
						return True
					current = drive_file_doc.parent_entity
					depth += 1
				except frappe.DoesNotExistError:
					return False
			
			return False
			
		except Exception:
			return False
	
	def get_parent_doc(self):
		"""
		Function: get_parent_doc
		Purpose: Safely get the parent Employer document
		Returns: Employer document or None
		"""
		if not self.parent:
			return None
		
		try:
			if frappe.db.exists("Employer", self.parent):
				return frappe.get_doc("Employer", self.parent)
		except (frappe.DoesNotExistError, frappe.ValidationError):
			pass
		
		return None
