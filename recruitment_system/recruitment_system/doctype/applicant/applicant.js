// Copyright (c) 2026, abdullahjavaid198@gmail.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Applicant", {
	refresh(frm) {
		// Additional refresh logic can be added here if needed
	},

	/**
	 * Event handler: Triggered when first_name field changes
	 * Operation: Auto-populates full_name field by combining first_name and last_name
	 */
	first_name(frm) {
		update_full_name(frm);
	},

	/**
	 * Event handler: Triggered when last_name field changes
	 * Operation: Auto-populates full_name field by combining first_name and last_name
	 */
	last_name(frm) {
		update_full_name(frm);
	},

	/**
	 * Event handler: Triggered when date_of_birth field changes
	 * Operation: Auto-calculates and updates age field based on date of birth
	 */
	date_of_birth(frm) {
		calculate_age(frm);
	},

	/**
	 * Event handler: Triggered when cnic field changes
	 * Operation: Auto-removes dashes and spaces from CNIC (format cleaning only, no validation)
	 * Note: Actual format validation happens on server-side during save
	 */
	cnic(frm) {
		clean_cnic_format(frm);
	},

	/**
	 * Event handler: Triggered when passport_number field changes
	 * Operation: Auto-converts passport number to uppercase (format cleaning only, no validation)
	 * Note: Actual format validation happens on server-side during save
	 */
	passport_number(frm) {
		clean_passport_format(frm);
	}
});

/**
 * Function: update_full_name
 * Purpose: Auto-populates the full_name field by combining first_name and last_name
 * Operation: Trims whitespace from both names, filters out empty values, and joins them with a space
 * Trigger: Called when first_name or last_name fields are changed
 */
function update_full_name(frm) {
	let first_name = frm.doc.first_name || "";
	let last_name = frm.doc.last_name || "";
	
	// Trim whitespace and combine names
	let full_name = [first_name.trim(), last_name.trim()].filter(Boolean).join(" ");
	
	// Update the field only if it's different to avoid unnecessary triggers
	if (frm.doc.full_name !== full_name) {
		frm.set_value("full_name", full_name);
	}
}

/**
 * Function: calculate_age
 * Purpose: Auto-calculates age from date of birth and updates the age field
 * Operation: Calculates the difference between current date and date of birth, adjusting for birthday not yet occurred
 * Trigger: Called when date_of_birth field is changed
 */
function calculate_age(frm) {
	let date_of_birth = frm.doc.date_of_birth;
	
	if (!date_of_birth) {
		frm.set_value("age", null);
		return;
	}
	
	// Calculate age from date of birth
	let birth_date = frappe.datetime.str_to_obj(date_of_birth);
	let today = frappe.datetime.get_today();
	let today_obj = frappe.datetime.str_to_obj(today);
	
	let age = today_obj.getFullYear() - birth_date.getFullYear();
	let month_diff = today_obj.getMonth() - birth_date.getMonth();
	
	// Adjust age if birthday hasn't occurred this year
	if (month_diff < 0 || (month_diff === 0 && today_obj.getDate() < birth_date.getDate())) {
		age--;
	}
	
	frm.set_value("age", age);
}

/**
 * Function: clean_cnic_format
 * Purpose: Auto-removes dashes and spaces from CNIC input for better user experience
 * Operation: Removes all dashes and spaces from CNIC value without throwing validation errors
 * Note: This only cleans the format while typing. Actual validation (13 digits) happens on server-side during save
 * Trigger: Called when cnic field is changed
 */
function clean_cnic_format(frm) {
	let cnic = frm.doc.cnic;
	
	if (!cnic) {
		return;
	}
	
	// Remove any dashes or spaces (format cleaning only, no validation)
	let cleaned_cnic = cnic.replace(/[-\s]/g, "");
	
	// Update the field with cleaned value (without dashes) if different
	if (cnic !== cleaned_cnic) {
		frm.set_value("cnic", cleaned_cnic);
	}
}

/**
 * Function: clean_passport_format
 * Purpose: Auto-converts passport number to uppercase for better user experience
 * Operation: Converts passport number to uppercase without throwing validation errors
 * Note: This only cleans the format while typing. Actual validation (2 letters + 7 digits) happens on server-side during save
 * Trigger: Called when passport_number field is changed
 */
function clean_passport_format(frm) {
	let passport_number = frm.doc.passport_number;
	
	if (!passport_number) {
		return;
	}
	
	// Convert to uppercase (format cleaning only, no validation)
	let cleaned_passport = passport_number.toUpperCase();
	
	// Update the field with cleaned value if different
	if (passport_number !== cleaned_passport) {
		frm.set_value("passport_number", cleaned_passport);
	}
}
