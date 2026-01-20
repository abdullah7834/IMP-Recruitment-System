# Copyright (c) 2026, abdullahjavaid198@gmail.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class Applicant(Document):
	def validate(self):
		"""
		Function: validate
		Purpose: Main validation method called by Frappe framework before saving the document
		Operation: Executes all validation methods in the correct order:
			1. Format validation (CNIC and Passport)
			2. Uniqueness validation (CNIC and Passport)
			3. Age calculation from date of birth
		"""
		self.validate_cnic_format()
		self.validate_passport_format()
		self.validate_unique_cnic()
		self.validate_unique_passport_number()
		self.calculate_age_from_dob()
	
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
