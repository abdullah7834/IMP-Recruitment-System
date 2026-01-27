# Copyright (c) 2026, abdullahjavaid198@gmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ApplicantDocument(Document):
	def after_insert(self):
		"""
		Function: after_insert
		Purpose: Handle file upload when a new document is added to Applicant Document child table
		Operation:
			- Only processes if parent Applicant is already saved (exists in database)
			- If parent doesn't exist yet, file processing will happen in parent's on_update hook
		Trigger: Called automatically after document is inserted into database
		"""
		# Only process if parent exists in database (already saved)
		if self.file and self.parent and frappe.db.exists("Applicant", self.parent):
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
		if self.has_value_changed("file"):
			old_file = self.get_doc_before_save().file if self.get_doc_before_save() else None
			new_file = self.file
			
			# Delete old file from Drive if it exists
			if old_file:
				# Use old document_type if available, otherwise current
				old_doc = self.get_doc_before_save()
				old_document_type = old_doc.get("document_type") if old_doc else self.document_type
				self.delete_drive_file(old_file, old_document_type)
			
			# Handle new file upload
			if new_file:
				self.handle_file_upload()
	
	def before_delete(self):
		"""
		Function: before_delete
		Purpose: Store file and document_type before deletion (data might not be available in on_trash)
		Operation: Stores file_url and document_type in flags for use in on_trash
		Trigger: Called automatically before document is deleted from database
		"""
		# Store data in flags so it's available in on_trash
		self.flags.file_to_delete = self.file
		self.flags.document_type_to_delete = self.document_type
		self.flags.parent_to_delete = self.parent
	
	def on_trash(self):
		"""
		Function: on_trash
		Purpose: Delete Drive file when document row is deleted
		Operation:
			- Finds the Drive file in the correct subfolder based on document_type
			- Deletes the file from Drive (soft delete - marks as inactive)
			- Does not delete the Applicant folder or other documents
		Trigger: Called automatically before document is deleted from database
		"""
		# Get file and document_type from flags (set in before_delete) or from self
		file_url = getattr(self.flags, 'file_to_delete', None) or (hasattr(self, 'file') and self.file)
		document_type = getattr(self.flags, 'document_type_to_delete', None) or (hasattr(self, 'document_type') and self.document_type)
		parent_name = getattr(self.flags, 'parent_to_delete', None) or (hasattr(self, 'parent') and self.parent)
		
		if file_url:
			# Always try to delete, even if document_type is missing (will search all folders)
			try:
				self.delete_drive_file(file_url, document_type, parent_name)
			except Exception as e:
				# Log error but don't prevent deletion
				frappe.log_error(
					f"Error in delete_drive_file for Applicant Document: {str(e)}\nFile URL: {file_url}\nDocument Type: {document_type}\n{frappe.get_traceback()}",
					"Drive File Deletion Error"
				)
		else:
			doc_name = getattr(self, 'name', 'unknown')
			frappe.log_error(
				f"No file URL found for Applicant Document {doc_name} during deletion",
				"Drive File Deletion Warning"
			)
	
	def handle_file_upload(self):
		"""
		Function: handle_file_upload
		Purpose: Move uploaded file to the correct Applicant Drive subfolder
		Operation:
			1. Get parent Applicant document
			2. Ensure Applicant folder structure exists
			3. Get correct subfolder based on document_type
			4. Create Drive File entry in the correct subfolder
		"""
		if not self.file or not self.document_type:
			return
		
		try:
			# Get parent Applicant document
			applicant = self.get_parent_doc()
			if not applicant:
				frappe.log_error(
					f"Cannot find parent Applicant for Applicant Document {self.name}",
					"Applicant Document File Upload Error"
				)
				return
			
			# Ensure Applicant folder structure exists (in case it wasn't created on insert)
			applicant.create_applicant_drive_folders()
			
			# Get Applicant's main folder
			applicant_folder_name = applicant.get_applicant_drive_folder()
			if not applicant_folder_name:
				frappe.log_error(
					f"Cannot find Drive folder for Applicant {applicant.name}",
					"Applicant Document File Upload Error"
				)
				return
			
			# Get subfolder name for this document type
			subfolder_name = applicant.get_document_subfolder(self.document_type)
			
			# Validate subfolder name (should always have a value, but check for safety)
			if not subfolder_name or not subfolder_name.strip():
				frappe.log_error(
					f"Invalid subfolder name for document type: {self.document_type}",
					"Applicant Document File Upload Error"
				)
				return
			
			# Log the mapping for debugging
			frappe.logger().debug(
				f"Mapping document type '{self.document_type}' to Drive folder '{subfolder_name}'"
			)
			
			# Get team
			team = applicant.get_drive_team()
			if not team:
				frappe.log_error(
					"No Drive team found for file upload",
					"Applicant Document File Upload Error"
				)
				return
			
			# Get or create subfolder
			subfolder_name_drive = applicant.get_or_create_drive_folder(subfolder_name, applicant_folder_name, team)
			
			# Find the File document
			file_doc = self.find_file_document()
			if not file_doc:
				frappe.log_error(
					f"Cannot find File document for {self.file}",
					"Applicant Document File Upload Error"
				)
				return
			
			# Create or move Drive File entry
			self.create_or_move_drive_file(file_doc, subfolder_name_drive, team)
			
		except Exception as e:
			frappe.log_error(
				f"Error handling file upload for Applicant Document {self.name}: {str(e)}\n{frappe.get_traceback()}",
				"Applicant Document File Upload Error"
			)
			# Don't throw error - allow document save to succeed
	
	def find_file_document(self):
		"""
		Function: find_file_document
		Purpose: Find the File document from the file URL
		Returns: File document or None
		"""
		if not self.file:
			return None
		
		return self._find_file_document_by_url(self.file)
	
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
		
		# Method 3: Lookup by attached_to (if parent is available)
		if not file_name and hasattr(self, 'parent') and self.parent:
			file_name = frappe.db.get_value(
				"File",
				{
					"attached_to_name": self.parent,
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
	
	def create_or_move_drive_file(self, file_doc, parent_folder, team):
		"""
		Function: create_or_move_drive_file
		Purpose: Create a Drive File entry for the uploaded file in the correct folder
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
			import os
			import mimetypes
			
			# Get file path
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
				mime_type = file_doc.content_type or "application/octet-stream"
			
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
			- parent_name: Parent Applicant name (optional, helps with lookup)
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
			
			# Get parent Applicant to find the correct folder structure
			# Use parent_name if provided (from before_delete), otherwise try to get from self
			if parent_name and frappe.db.exists("Applicant", parent_name):
				try:
					applicant = frappe.get_doc("Applicant", parent_name)
				except:
					applicant = None
			else:
				applicant = self.get_parent_doc()
			
			if not applicant:
				# If parent doesn't exist, try to find Drive File by title only (fallback)
				# Search across all teams (last resort)
				drive_file_name = frappe.db.get_value(
					"Drive File",
					{
						"title": file_doc.file_name,
						"is_active": 1,
						"is_group": 0
					},
					"name",
					order_by="creation desc"
				)
			else:
				# Get Applicant's main folder
				applicant_folder = applicant.get_applicant_drive_folder()
				
				if not applicant_folder:
					# Fallback: search by title only (with team filter if available)
					team = applicant.get_drive_team()
					filters = {
						"title": file_doc.file_name,
						"is_active": 1,
						"is_group": 0
					}
					if team:
						filters["team"] = team
					
					drive_file_name = frappe.db.get_value(
						"Drive File",
						filters,
						"name",
						order_by="creation desc"
					)
				else:
					# Use document_type to find the specific subfolder
					if document_type:
						# Get the subfolder name for this document type
						subfolder_name = applicant.get_document_subfolder(document_type)
						
						if subfolder_name:
							# Find the specific subfolder
							subfolder_drive = frappe.db.get_value(
								"Drive File",
								{
									"title": subfolder_name,
									"parent_entity": applicant_folder,
									"is_group": 1,
									"is_active": 1
								},
								"name"
							)
							
							if subfolder_drive:
								# Search in the specific subfolder first (most accurate)
								# Try exact file name match first (with team filter)
								team = applicant.get_drive_team()
								filters = {
									"title": file_doc.file_name,
									"parent_entity": subfolder_drive,
									"is_active": 1,
									"is_group": 0
								}
								if team:
									filters["team"] = team
								
								drive_file_name = frappe.db.get_value(
									"Drive File",
									filters,
									"name",
									order_by="creation desc"
								)
								
								# If not found, try searching by file name pattern (in case Drive renamed it)
								if not drive_file_name:
									# Get all files in the subfolder and match by name pattern
									filters = {
										"parent_entity": subfolder_drive,
										"is_active": 1,
										"is_group": 0
									}
									if team:
										filters["team"] = team
									
									all_files = frappe.get_all(
										"Drive File",
										filters=filters,
										fields=["name", "title"]
									)
									
									# Try to find file by matching file name (case-insensitive, partial match)
									file_name_lower = file_doc.file_name.lower()
									for df in all_files:
										if df.get("title") and file_name_lower in df.get("title", "").lower():
											drive_file_name = df.get("name")
											break
								
								# If still not found, search in all subfolders
								if not drive_file_name:
									drive_file_name = self._search_drive_file_in_all_subfolders(
										file_doc.file_name, applicant_folder, team
									)
							else:
								# Subfolder doesn't exist, search in all subfolders
								team = applicant.get_drive_team()
								drive_file_name = self._search_drive_file_in_all_subfolders(
									file_doc.file_name, applicant_folder, team
								)
						else:
							# No subfolder mapping, search in all subfolders
							team = applicant.get_drive_team()
							drive_file_name = self._search_drive_file_in_all_subfolders(
								file_doc.file_name, applicant_folder, team
							)
					else:
						# No document_type provided, search in all subfolders
						team = applicant.get_drive_team()
						drive_file_name = self._search_drive_file_in_all_subfolders(
							file_doc.file_name, applicant_folder, team
						)
			
			# If still not found, try one more comprehensive search
			if not drive_file_name and applicant and applicant_folder:
				team = applicant.get_drive_team()
				drive_file_name = self._comprehensive_drive_file_search(
					file_doc, applicant_folder, document_type, team
				)
			
			if drive_file_name:
				try:
					drive_file_doc = frappe.get_doc("Drive File", drive_file_name)
					# Soft delete (mark as inactive)
					drive_file_doc.is_active = 0
					drive_file_doc.save(ignore_permissions=True)
					
					# Log success with more details
					frappe.log_error(
						f"Successfully deleted Drive file '{file_doc.file_name}' (Drive File: {drive_file_name}) from folder '{document_type or 'unknown'}' for Applicant Document {getattr(self, 'name', 'unknown')}",
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
					"applicant_folder": applicant.get_applicant_drive_folder() if applicant else None
				}
				frappe.log_error(
					f"Drive file '{file_doc.file_name}' not found in Drive folders. Debug info: {debug_info}",
					"Drive File Not Found Warning"
				)
			
		except Exception as e:
			frappe.log_error(
				f"Error deleting Drive file {file_url}: {str(e)}\n{frappe.get_traceback()}",
				"Applicant Document File Deletion Error"
			)
	
	def _comprehensive_drive_file_search(self, file_doc, applicant_folder, document_type=None, team=None):
		"""
		Function: _comprehensive_drive_file_search
		Purpose: Comprehensive search for Drive file using multiple criteria
		Parameters:
			- file_doc: File document
			- applicant_folder: Applicant's main Drive folder name
			- document_type: Document type (optional)
			- team: Drive team name (optional, for better filtering)
		Returns: Drive File document name or None
		"""
		# Get all subfolders
		all_subfolders = frappe.get_all(
			"Drive File",
			filters={
				"parent_entity": applicant_folder,
				"is_group": 1,
				"is_active": 1
			},
			fields=["name", "title"]
		)
		
		subfolder_ids = [sf["name"] for sf in all_subfolders]
		subfolder_ids.append(applicant_folder)
		
		# Search by file name (exact and partial match)
		filters = {
			"parent_entity": ["in", subfolder_ids],
			"is_active": 1,
			"is_group": 0
		}
		if team:
			filters["team"] = team
		
		all_drive_files = frappe.get_all(
			"Drive File",
			filters=filters,
			fields=["name", "title", "path", "mime_type"]
		)
		
		file_name_lower = file_doc.file_name.lower()
		file_name_base = file_name_lower.rsplit('.', 1)[0] if '.' in file_name_lower else file_name_lower
		
		for df in all_drive_files:
			title = (df.get("title") or "").lower()
			path = (df.get("path") or "").lower()
			
			# Match by exact title
			if title == file_name_lower:
				return df.get("name")
			
			# Match by title containing file name (without extension)
			if file_name_base in title or file_name_lower in title:
				return df.get("name")
			
			# Match by path containing file name
			if file_name_lower in path or file_name_base in path:
				return df.get("name")
		
		return None
	
	def _search_drive_file_in_all_subfolders(self, file_name, applicant_folder, team=None):
		"""
		Function: _search_drive_file_in_all_subfolders
		Purpose: Search for a Drive file in all subfolders of an Applicant folder
		Parameters:
			- file_name: Name of the file to search for
			- applicant_folder: Applicant's main Drive folder name
			- team: Drive team name (optional, for better filtering)
		Returns: Drive File document name or None
		"""
		# Get all subfolders
		subfolders = frappe.get_all(
			"Drive File",
			filters={
				"parent_entity": applicant_folder,
				"is_group": 1,
				"is_active": 1
			},
			fields=["name"]
		)
		
		# Search in all subfolders
		subfolder_names = [sf["name"] for sf in subfolders]
		subfolder_names.append(applicant_folder)  # Also check main folder
		
		# First try exact match
		filters = {
			"title": file_name,
			"parent_entity": ["in", subfolder_names],
			"is_active": 1,
			"is_group": 0
		}
		if team:
			filters["team"] = team
		
		drive_file_name = frappe.db.get_value(
			"Drive File",
			filters,
			"name",
			order_by="creation desc"
		)
		
		# If not found, try pattern matching (case-insensitive)
		if not drive_file_name:
			file_name_lower = file_name.lower()
			file_name_base = file_name_lower.rsplit('.', 1)[0] if '.' in file_name_lower else file_name_lower
			
			all_files = frappe.get_all(
				"Drive File",
				filters=filters,
				fields=["name", "title"]
			)
			
			for df in all_files:
				title = (df.get("title") or "").lower()
				if title == file_name_lower or file_name_base in title or file_name_lower in title:
					drive_file_name = df.get("name")
					break
		
		return drive_file_name
	
	def get_parent_doc(self):
		"""
		Function: get_parent_doc
		Purpose: Get the parent Applicant document
		Returns: Applicant document or None
		"""
		if not self.parent:
			return None
		
		# Verify this is actually an Applicant child table
		if hasattr(self, 'parenttype') and self.parenttype != "Applicant":
			return None
		
		# Check if parent exists in database first
		if not frappe.db.exists("Applicant", self.parent):
			return None
		
		try:
			return frappe.get_doc("Applicant", self.parent)
		except (frappe.DoesNotExistError, frappe.ValidationError):
			return None
