// Copyright (c) 2026, abdullahjavaid198@gmail.com and contributors
// For license information, please see license.txt

/**
 * Custom JavaScript for Job Applicant DocType
 * Extends standard Job Applicant functionality for overseas recruitment
 */

/**
 * Sync current_stage_name from Pipeline Stage so depends_on for date fields evaluates correctly.
 * Refreshes Company Selection Date, Offer Letter Received Date, Offer Letter Accepted Date.
 */
function sync_current_stage_name_and_refresh_date_fields(frm) {
	if (!frm.doc.current_stage) {
		frm.doc.current_stage_name = null;
		frm.refresh_field("current_stage_name");
		refresh_date_fields(frm);
		return;
	}
	frappe.call({
		method: "recruitment_system.recruitment_system.doctype.job_applicant.job_applicant.get_stage_name",
		args: { stage_link_value: frm.doc.current_stage },
		callback: function(r) {
			frm.doc.current_stage_name = r.message || null;
			frm.refresh_field("current_stage_name");
			refresh_date_fields(frm);
		}
	});
}

function refresh_date_fields(frm) {
	var date_fields = ["Company_selection_date", "offer_letter_received_date", "offer_letter_accepted_date"];
	date_fields.forEach(function(fieldname) {
		if (frm.fields_dict[fieldname]) {
			frm.refresh_field(fieldname);
		}
	});
}

/**
 * When pipeline is Visa Process (or visa_process is linked), make Offer Letter / selection date
 * fields read-only so they remain visible as historical data and are not accidentally edited.
 */
function set_offer_letter_dates_readonly_when_visa_process(frm) {
	var date_fields = ["Company_selection_date", "offer_letter_received_date", "offer_letter_accepted_date"];
	var read_only = !!(frm.doc.pipeline === "Visa Process" && frm.doc.visa_process);
	date_fields.forEach(function(fieldname) {
		if (frm.fields_dict[fieldname]) {
			frm.set_df_property(fieldname, "read_only", read_only ? 1 : 0);
		}
	});
}

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
		
		// Handle checkbox locking and form read-only state
		setup_checkbox_controls(frm);

		// Track pipeline so we only clear Current Stage when pipeline actually changes (not on load/refresh)
		frm._last_pipeline = frm.doc.pipeline;
		// Filter Current Stage by selected Pipeline (Link field expects filters as object: { fieldname: value } or { fieldname: [operator, value] })
		if (frm.fields_dict.pipeline && frm.fields_dict.current_stage) {
			if (frm.doc.pipeline && typeof frm.doc.pipeline === "string") {
				frm.set_df_property("current_stage", "filters", { pipeline: frm.doc.pipeline });
			} else {
				frm.set_df_property("current_stage", "filters", {});
			}
		}
		// Sync current_stage_name so date fields (Offer Letter / Visa Process) visibility is correct
		if (frm.doc.current_stage || frm.doc.pipeline === "Offer Letter" || frm.doc.pipeline === "Visa Process") {
			sync_current_stage_name_and_refresh_date_fields(frm);
		}
		// When in Visa Process pipeline: show Offer Letter dates as historical (read-only) so they stay visible
		set_offer_letter_dates_readonly_when_visa_process(frm);
		
		// Add "Schedule Company Interview" when candidate is Internally Selected (second round from Job Applicant)
		if (frm.doc.pipeline === "Interviews" && frm.doc.current_stage && !frm.is_new()) {
			frappe.call({
				method: "recruitment_system.recruitment_system.doctype.job_applicant.job_applicant.get_job_applicant_current_stage_name",
				args: { name: frm.doc.name },
				callback: function(r) {
					if (r.message === "Internally Selected") {
						frm.add_custom_button(__("Schedule Company Interview"), function() {
							schedule_Company_interview(frm);
						}, __("Actions"));
					}
				}
			});
		}

		// Add "Start Visa Process" button when stage is Offer Letter Accepted and no Visa Process yet
		if (frm.doc.pipeline === "Offer Letter" && frm.doc.current_stage && !frm.doc.visa_process && !frm.is_new()) {
			frm.add_custom_button(__("Start Visa Process"), function() {
				start_visa_process(frm);
			}, __("Actions"));
		}
		
		// Open Visa Process if linked
		if (frm.doc.visa_process) {
			frm.add_custom_button(__("Open Visa Process"), function() {
				frappe.set_route("Form", "Visa Process", frm.doc.visa_process);
			}, __("Actions"));
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
	 * When Pipeline changes: filter Current Stage to this pipeline; set Current Stage to
	 * first stage of the new pipeline (from DB) so values are always from database.
	 */
	pipeline: function(frm) {
		if (!frm.fields_dict.current_stage) return;
		if (frm.doc.pipeline && typeof frm.doc.pipeline === "string") {
			frm.set_df_property("current_stage", "filters", { pipeline: frm.doc.pipeline });
		} else {
			frm.set_df_property("current_stage", "filters", {});
		}
		var pipeline_changed = frm._last_pipeline !== undefined && frm.doc.pipeline !== frm._last_pipeline;
		frm._last_pipeline = frm.doc.pipeline;
		if (pipeline_changed && frm.doc.pipeline) {
			// Set Current Stage to first stage of the selected pipeline (from DB)
			frappe.call({
				method: "recruitment_system.recruitment_system.doctype.job_applicant.job_applicant.get_first_stage_for_pipeline",
				args: { pipeline_name: frm.doc.pipeline },
				callback: function(r) {
					if (r.message) {
						frm.set_value("current_stage", r.message);
					} else {
						frm.set_value("current_stage", "");
					}
					frm.refresh_field("current_stage");
					sync_current_stage_name_and_refresh_date_fields(frm);
				}
			});
			return;
		}
		if (pipeline_changed && !frm.doc.pipeline) {
			frm.set_value("current_stage", "");
		}
		frm.refresh_field("current_stage");
	},
	/**
	 * When Current Stage changes: sync current_stage_name so date fields (Offer Letter Received/Accepted) show/hide correctly.
	 */
	current_stage: function(frm) {
		sync_current_stage_name_and_refresh_date_fields(frm);
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
	},
	/**
	 * Event handler: Triggered when job_title (Job Opening Link) field changes directly
	 * Operation: Fetches and populates job_opening_title from the selected Job Opening
	 */
	job_title: function(frm) {
		if (!frm.doc.job_title) {
			// Clear job_opening_title if job_title is cleared
			if (frm.fields_dict.job_opening_title) {
				frm.set_value("job_opening_title", "");
			}
			return;
		}
		
		// Fetch Job Opening details to get the job_title field
		frappe.call({
			method: "frappe.Company.get",
			args: {
				doctype: "Job Opening",
				name: frm.doc.job_title
			},
			callback: function(r) {
				if (r.message && r.message.job_title && frm.fields_dict.job_opening_title) {
					// Populate Job Opening Title from the Job Opening's job_title field
					frm.set_value("job_opening_title", r.message.job_title);
				}
			},
			error: function(r) {
				console.error("[Job Applicant] Error fetching Job Opening details:", r);
			}
		});
	},
	/**
	 * When "Ready for Application Pipeline" is checked: auto-set Pipeline = Interviews
	 * and Current Stage = Screening (first stage). Server validates and persists on save.
	 */
	ready_for_pipeline: function(frm) {
		if (frm.doc.ready_for_pipeline) {
			frappe.call({
				method: "recruitment_system.recruitment_system.doctype.job_applicant.job_applicant.get_initial_pipeline_and_stage",
				callback: function(r) {
					var msg = r.message;
					if (msg && msg.pipeline && msg.current_stage) {
						// Set pipeline first (triggers pipeline handler; it clears current_stage)
						frm.set_value("pipeline", msg.pipeline);
						frm.set_value("current_stage", msg.current_stage);
						// Apply filters so Current Stage dropdown shows only stages for this pipeline
						if (frm.fields_dict.current_stage) {
							frm.set_df_property("current_stage", "filters", { pipeline: msg.pipeline });
						}
						frm.refresh_field("pipeline");
						frm.refresh_field("current_stage");
						frappe.show_alert({
							indicator: "green",
							message: __("Pipeline set to {0}, stage set to first stage.", [msg.pipeline])
						}, 3);
					} else {
						frappe.msgprint({
							title: __("Setup Required"),
							message: __("No pipeline for Job Applicant or no stages found. Run 'Setup Pipelines and Stages' from the Recruitment System module."),
							indicator: "orange"
						});
					}
				}
			});
			// Passport expiry warning when applicable
			if (frm.doc.applicant && !frm.is_new()) {
				frappe.call({
					method: "recruitment_system.recruitment_system.doctype.job_applicant.job_applicant.get_passport_expiry_warning",
					args: { name: frm.doc.name, applicant: frm.doc.applicant },
					callback: function(r) {
						if (r.message && r.message.has_warning) {
							frappe.msgprint({
								title: __("Passport Expiry Warning"),
								message: r.message.message,
								indicator: "orange"
							});
						}
					},
					error: function() {}
				});
			}
		} else {
			frm.set_value("pipeline", "");
			frm.set_value("current_stage", "");
			if (frm.fields_dict.current_stage) {
				frm.set_df_property("current_stage", "filters", {});
			}
			frm.refresh_field("pipeline");
			frm.refresh_field("current_stage");
		}
	},
	/**
	 * Event handler: Triggered when converted_to_application checkbox changes
	 * Operation: Lock form and prevent further changes
	 */
	converted_to_application: function(frm) {
		if (frm.doc.converted_to_application) {
			frm.set_read_only();
			frm.disable_save();
			frappe.show_alert({
				indicator: "green",
				message: __("Job Applicant has been converted to Application. Form is now read-only.")
			}, 5);
		}
	}
});

/**
 * Setup checkbox controls and locking logic
 */
function setup_checkbox_controls(frm) {
	// Lock converted_to_application checkbox (system-controlled)
	if (frm.fields_dict.converted_to_application) {
		if (frm.doc.converted_to_application) {
			// Already converted - make read-only
			frm.set_df_property("converted_to_application", "read_only", 1);
		} else {
			// Not converted yet - keep read-only (system-controlled)
			frm.set_df_property("converted_to_application", "read_only", 1);
		}
	}
	
	// ready_for_pipeline is user-controlled, but validation happens server-side
	// No need to lock it here - server validation will prevent invalid states
}

/**
 * Open new Interview form for Company round (second round) from Job Applicant.
 * Pre-fills all fields from Job Applicant (same as first interview): job_applicant, job_opening, demand,
 * interview_round, interview_level. Interview form reads sessionStorage and populates fields.
 */
function schedule_Company_interview(frm) {
	frappe.call({
		method: "recruitment_system.recruitment_system.doctype.job_applicant.job_applicant.get_default_Company_interview_round",
		callback: function(r) {
			var default_round = r.message || null;
			// Store Job Applicant context so Interview form onload can pre-fill all fields (same as first interview)
			var interview_data = {
				job_applicant: frm.doc.name,
				job_opening: frm.doc.job_title || "",
				demand: frm.doc.linked_demand || "",
				interview_round: default_round || "",
				interview_level: "Company"
			};
			try {
				sessionStorage.setItem("interview_from_job_applicant", JSON.stringify(interview_data));
			} catch (e) {
				console.warn("Could not set sessionStorage for interview pre-fill:", e);
			}
			frappe.model.with_doctype("Interview", function() {
				var doc = frappe.model.get_new_doc("Interview");
				doc.job_applicant = frm.doc.name;
				doc.interview_level = "Company";
				if (default_round) {
					doc.interview_round = default_round;
				}
				frappe.set_route("Form", "Interview", doc.name);
			});
		}
	});
}

/**
 * Start Visa Process from Job Applicant (when stage is Offer Letter Accepted)
 */
function start_visa_process(frm) {
	frappe.confirm(
		__("Start Visa Process for this candidate? A Visa Process document will be created."),
		function() {
			frm.call({
				method: "recruitment_system.recruitment_system.doctype.job_applicant.job_applicant.start_visa_process",
				args: { job_applicant_name: frm.doc.name },
				freeze: true,
				freeze_message: __("Creating Visa Process..."),
				callback: function(r) {
					if (r.message && r.message.success) {
						frappe.show_alert({
							indicator: "green",
							message: __("Visa Process '{0}' created.", [r.message.visa_process])
						}, 5);
						frm.reload_doc();
						if (r.message.visa_process) {
							setTimeout(function() {
								frappe.set_route("Form", "Visa Process", r.message.visa_process);
							}, 1000);
						}
					}
				}
			});
		}
	);
}
