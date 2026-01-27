// Copyright (c) 2026, abdullahjavaid198@gmail.com and contributors
// For license information, please see license.txt

/**
 * Custom JavaScript for Job Applicant DocType
 * Extends standard Job Applicant functionality for overseas recruitment
 */

// Function to fetch and populate applicant details
function fetch_and_populate_applicant_details(frm) {
	if (!frm.doc.applicant) {
		return;
	}
	
	// Fetch Applicant data from server
	frappe.call({
		method: "recruitment_system.recruitment_system.doctype.job_applicant_custom_fields.add_custom_fields.get_applicant_details",
		args: {
			applicant_id: frm.doc.applicant
		},
		callback: function(r) {
			if (r.message) {
				let applicant_data = r.message;
				let fields_updated = [];
				
				// Populate applicant_name from full_name (only if empty)
				if (applicant_data.full_name && frm.fields_dict.applicant_name) {
					if (!frm.doc.applicant_name || frm.doc.applicant_name.trim() === "") {
						frm.set_value("applicant_name", applicant_data.full_name);
						fields_updated.push("Applicant Name");
					}
				}
				
				// Populate email_id from email_address (only if empty)
				if (applicant_data.email_address && frm.fields_dict.email_id) {
					if (!frm.doc.email_id || frm.doc.email_id.trim() === "") {
						frm.set_value("email_id", applicant_data.email_address);
						fields_updated.push("Email Address");
					}
				}
				
				// Populate phone_number from mobile_number (only if empty)
				if (applicant_data.mobile_number && frm.fields_dict.phone_number) {
					if (!frm.doc.phone_number || frm.doc.phone_number.trim() === "") {
						frm.set_value("phone_number", applicant_data.mobile_number);
						fields_updated.push("Phone Number");
					}
				}
				
				// Show success message only if fields were updated
				if (fields_updated.length > 0) {
					frappe.show_alert({
						message: __("Fetched and populated: {0}", [fields_updated.join(", ")]),
						indicator: "green"
					}, 3);
				} else {
					// All fields already have values
					frappe.show_alert({
						message: __("Applicant details fetched. Fields already populated."),
						indicator: "blue"
					}, 2);
				}
			} else {
				console.error("[Job Applicant] No data in response message:", r);
			}
		},
		error: function(r) {
			console.error("[Job Applicant] Error fetching details:", r);
			frappe.msgprint({
				title: __("Error"),
				message: __("Error fetching Applicant details: {0}", [r.message || "Unknown error"]),
				indicator: "red"
			});
		}
	});
}

frappe.ui.form.on("Job Applicant", {
	refresh: function(frm) {
		// Check if applicant field exists
		if (frm.fields_dict.applicant) {
			// Manually attach change event if not already attached
			if (frm.fields_dict.applicant.$input) {
				frm.fields_dict.applicant.$input.off('change.applicant_autofill').on('change.applicant_autofill', function() {
					fetch_and_populate_applicant_details(frm);
				});
			}
			
			// If applicant is already selected but fields are empty, try to fetch
			if (frm.doc.applicant && (!frm.doc.applicant_name || !frm.doc.email_id || !frm.doc.phone_number)) {
				fetch_and_populate_applicant_details(frm);
			}
		}
		
		// Silently load positions on form refresh if demand is already selected
		if (frm.doc.linked_demand && frm.fields_dict.demand_position) {
			if (!frm.fields_dict.demand_position.df.options) {
				// Set silent mode flag before triggering
				frm._silent_load_positions = true;
				frm.trigger("linked_demand");
			}
		}
	},
	/**
	 * Event handler: Triggered when applicant (Link to Applicant) field changes
	 * Operation: Auto-fetches and populates applicant_name, email_id, and phone_number
	 * from the selected Applicant master record
	 * Uses fetch_if_empty logic: only populates if fields are empty
	 */
	applicant: function(frm) {
		if (!frm.doc.applicant) {
			// Don't clear fields if applicant is cleared (user might have edited them)
			return;
		}
		
		// Use the shared function
		fetch_and_populate_applicant_details(frm);
	},
	/**
	 * Event handler: Triggered when linked_demand (Link to Demand) field changes
	 * Operation: Fetches positions from the selected Demand and populates demand_position dropdown
	 */
	linked_demand: function(frm) {
		if (!frm.doc.linked_demand) {
			// Clear demand_position if demand is cleared
			frm.set_value("demand_position", "");
			frm.set_df_property("demand_position", "options", "");
			frm.refresh_field("demand_position");
			return;
		}
		
		// Check if this is being called from refresh (silent mode)
		var silent_mode = frm._silent_load_positions || false;
		
		// Fetch positions from the selected Demand
		frappe.call({
			method: "recruitment_system.recruitment_system.doctype.job_opening_demand.job_opening_demand.get_demand_positions",
			args: {
				demand_name: frm.doc.linked_demand
			},
			callback: function(r) {
				if (r.message && r.message.length > 0) {
					var options = [];
					for (var i = 0; i < r.message.length; i++) {
						if (r.message[i].job_title) {
							options.push(r.message[i].job_title);
						}
					}
					
					// Update the Select field options
					frm.set_df_property("demand_position", "options", options.join("\n"));
					
					// Only clear and show alert if not in silent mode (i.e., user actually changed the field)
					if (!silent_mode) {
						frm.set_value("demand_position", "");
						
						if (options.length > 0) {
							frappe.show_alert({
								indicator: "green",
								message: __("Found {0} position(s). Please select a position.", [options.length])
							}, 3);
						}
					}
				} else {
					// No positions found
					frm.set_df_property("demand_position", "options", "");
					
					// Only show alert if not in silent mode
					if (!silent_mode) {
						frm.set_value("demand_position", "");
						frappe.show_alert({
							indicator: "orange",
							message: __("No positions found in this Demand.")
						}, 3);
					}
				}
				
				frm.refresh_field("demand_position");
				
				// Reset silent mode flag
				frm._silent_load_positions = false;
			},
			error: function(r) {
				// Reset silent mode flag
				frm._silent_load_positions = false;
				
				// Only show error if not in silent mode
				if (!silent_mode) {
					frappe.msgprint({
						title: __("Error"),
						message: __("Error fetching Demand Positions: {0}", [r.message || "Unknown error"]),
						indicator: "red"
					});
				}
			}
		});
	},
	/**
	 * Event handler: Triggered when demand_position (Select) field changes
	 * Operation: Finds and populates job_opening field based on selected demand and position
	 */
	demand_position: function(frm) {
		if (!frm.doc.linked_demand || !frm.doc.demand_position) {
			// Clear job_title (Job Opening) and job_opening_title if position is cleared
			if (!frm.doc.demand_position) {
				if (frm.fields_dict.job_title) {
					frm.set_value("job_title", "");
				}
				if (frm.fields_dict.job_opening_title) {
					frm.set_value("job_opening_title", "");
				}
			}
			return;
		}
		
		// Find Job Opening that matches the selected demand and position
		frappe.call({
			method: "recruitment_system.recruitment_system.doctype.job_applicant_custom_fields.add_custom_fields.get_job_opening_by_demand_position",
			args: {
				demand_name: frm.doc.linked_demand,
				demand_position: frm.doc.demand_position
			},
			callback: function(r) {
				if (r.message && r.message.name) {
					// Job Opening found - populate the fields
					frm.set_value("job_title", r.message.name);
					
					// Populate Job Opening Title from the Job Opening's job_title field
					if (r.message.job_title && frm.fields_dict.job_opening_title) {
						frm.set_value("job_opening_title", r.message.job_title);
					}
					
					frappe.show_alert({
						indicator: "green",
						message: __("Job Opening '{0}' found and selected.", [r.message.name])
					}, 3);
				} else {
					// No Job Opening found - clear fields and show info message
					if (frm.fields_dict.job_title) {
						frm.set_value("job_title", "");
					}
					if (frm.fields_dict.job_opening_title) {
						frm.set_value("job_opening_title", "");
					}
					
					frappe.show_alert({
						indicator: "blue",
						message: __("Job Opening is not found for this Demand Position.")
					}, 4);
				}
			},
			error: function(r) {
				frappe.msgprint({
					title: __("Error"),
					message: __("Error fetching Job Opening: {0}", [r.message || "Unknown error"]),
					indicator: "red"
				});
			}
		});
	}
});
