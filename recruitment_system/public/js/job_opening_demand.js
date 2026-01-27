// Copyright (c) 2026, abdullahjavaid198@gmail.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Job Opening", {
	linked_demand: function(frm) {
		if (!frm.doc.linked_demand) {
			frm.set_value("demand_position", "");
			return;
		}
		
		// Check if this is being called from refresh (silent mode)
		var silent_mode = frm._silent_load_positions || false;
		
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
					
					frm.set_df_property("demand_position", "options", options.join("\n"));
					
					// Only clear and show alert if not in silent mode (i.e., user actually changed the field)
					if (!silent_mode) {
						frm.set_value("demand_position", "");
						
						if (options.length > 0) {
							frappe.show_alert({
								indicator: "green",
								message: __("Found {0} position(s). Please select a position.", [options.length])
							});
						}
					}
				} else {
					frm.set_df_property("demand_position", "options", "");
					
					// Only show alert if not in silent mode
					if (!silent_mode) {
						frm.set_value("demand_position", "");
						frappe.show_alert({
							indicator: "orange",
							message: __("No positions found in this Demand.")
						});
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
	
	demand_position: function(frm) {
		if (!frm.doc.linked_demand || !frm.doc.demand_position) {
			return;
		}
		
		frappe.call({
			method: "recruitment_system.recruitment_system.doctype.job_opening_demand.job_opening_demand.get_demand_position_details",
			args: {
				demand_name: frm.doc.linked_demand,
				position_job_title: frm.doc.demand_position
			},
			callback: function(r) {
				if (r.message) {
					var position = r.message;
					
					frm.set_value({
						"job_title": position.job_title || "",
						"experience_required": position.experience_required || "",
						"education_required": position.education_required || "",
						"planned_vacancies": position.quantity || 0
					});
					
					if (position.basic_sallary) {
						var salary = parseFloat(position.basic_sallary);
						if (!isNaN(salary) && frm.fields_dict.lower_range) {
							frm.set_value("lower_range", salary);
						}
					}
					
					frappe.call({
						method: "recruitment_system.recruitment_system.doctype.job_opening_demand.job_opening_demand.get_demand_age_requirements",
						args: {
							demand_name: frm.doc.linked_demand
						},
						callback: function(age_r) {
							if (age_r.message) {
								if (frm.fields_dict.age_min && age_r.message.age_min) {
									frm.set_value("age_min", age_r.message.age_min);
								}
								if (frm.fields_dict.age_max && age_r.message.age_max) {
									frm.set_value("age_max", age_r.message.age_max);
								}
							}
							frm.refresh_fields();
						}
					});
					
					frappe.show_alert({
						indicator: "green",
						message: __("Job Opening fields auto-filled from Demand Position.")
					});
				} else {
					frappe.show_alert({
						indicator: "orange",
						message: __("Position details not found.")
					});
				}
			},
			error: function(r) {
				frappe.msgprint({
					title: __("Error"),
					message: __("Error fetching Position details: {0}", [r.message || "Unknown error"]),
					indicator: "red"
				});
			}
		});
	},
	
	refresh: function(frm) {
		// Silently load positions on form refresh (without showing alerts)
		if (frm.doc.linked_demand && frm.fields_dict.demand_position) {
			if (!frm.fields_dict.demand_position.df.options) {
				// Set silent mode flag before triggering
				frm._silent_load_positions = true;
				frm.trigger("linked_demand");
			}
		}
	}
});
