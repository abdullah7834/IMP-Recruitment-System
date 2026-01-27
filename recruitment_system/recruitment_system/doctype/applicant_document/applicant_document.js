// Copyright (c) 2026, abdullahjavaid198@gmail.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Applicant Document", {
	/**
	 * Event handler: Triggered when document_type field changes
	 * Operation: Shows/hides fields conditionally based on document type
	 */
	document_type(frm) {
		toggle_fields_based_on_document_type(frm);
	},

	/**
	 * Event handler: Triggered when form is refreshed
	 * Operation: Ensures fields are shown/hidden correctly based on current document_type
	 */
	refresh(frm) {
		toggle_fields_based_on_document_type(frm);
	}
});

/**
 * Function: toggle_fields_based_on_document_type
 * Purpose: Show/hide fields conditionally based on the selected document type
 * Operation:
 *   - Documents with expiry dates (Passport, CNIC, License, Visa, Work Permit): Show issue_date, expiry_date, document_number, valid
 *   - Documents with validity (Certificate): Show valid field
 *   - Other documents (CV, Education, Experience, etc.): Hide date and number fields
 * Trigger: Called when document_type changes or form refreshes
 */
function toggle_fields_based_on_document_type(frm) {
	if (!frm.doc.document_type) {
		// Hide all conditional fields if no document type selected
		hide_conditional_fields(frm);
		return;
	}

	const document_type = frm.doc.document_type;

	// Documents that have issue date, expiry date, and document number
	const documents_with_dates = ["Passport", "CNIC", "License", "Visa", "Work Permit"];
	
	// Documents that have validity checkbox
	const documents_with_validity = ["Passport", "CNIC", "License", "Visa", "Work Permit", "Certificate"];

	// Show/hide fields based on document type
	if (documents_with_dates.includes(document_type)) {
		// Show date and number fields
		frm.set_df_property("issue_date", "hidden", 0);
		frm.set_df_property("expiry_date", "hidden", 0);
		frm.set_df_property("document_number", "hidden", 0);
		frm.set_df_property("valid", "hidden", 0);
	} else {
		// Hide date and number fields
		frm.set_df_property("issue_date", "hidden", 1);
		frm.set_df_property("expiry_date", "hidden", 1);
		frm.set_df_property("document_number", "hidden", 1);
		
		// Show valid field only for Certificate
		if (documents_with_validity.includes(document_type)) {
			frm.set_df_property("valid", "hidden", 0);
		} else {
			frm.set_df_property("valid", "hidden", 1);
		}
	}

	// Verified field is always visible
	frm.set_df_property("verified", "hidden", 0);
}

/**
 * Function: hide_conditional_fields
 * Purpose: Hide all conditional fields when no document type is selected
 * Operation: Hides issue_date, expiry_date, document_number, and valid fields
 */
function hide_conditional_fields(frm) {
	frm.set_df_property("issue_date", "hidden", 1);
	frm.set_df_property("expiry_date", "hidden", 1);
	frm.set_df_property("document_number", "hidden", 1);
	frm.set_df_property("valid", "hidden", 1);
}
