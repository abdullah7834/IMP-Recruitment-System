// Copyright (c) 2026, abdullahjavaid198@gmail.com and contributors
// For license information, please see license.txt

/**
 * Custom JavaScript for Interview DocType
 * Handles auto-population from Job Applicant and form initialization.
 * Application doctype was removed; Interview links only to Job Applicant.
 */

frappe.ui.form.on("Interview", {
	before_load: function(frm) {
		if (frm.is_new()) {
			const stored_data = sessionStorage.getItem("interview_from_job_applicant") || sessionStorage.getItem("interview_from_application");
			if (stored_data) {
				try {
					const interview_data = JSON.parse(stored_data);
					frm._preserved_job_applicant = interview_data.job_applicant;
					frm._preserved_job_opening = interview_data.job_opening;
					frm._preserved_demand = interview_data.demand;
				} catch (e) {
					console.error("Error parsing interview data:", e);
				}
			}
		}
	},

	onload: function(frm) {
		if (frm.is_new()) {
			frm._suppress_validation = true;
			frm._preserved_job_applicant = null;
			frm._preserved_job_opening = null;
			frm._preserved_demand = null;

			const stored_data = sessionStorage.getItem("interview_from_job_applicant") || sessionStorage.getItem("interview_from_application");
			if (stored_data) {
				try {
					const interview_data = JSON.parse(stored_data);
					if (interview_data.job_applicant) {
						frm._preserved_job_applicant = interview_data.job_applicant;
					}
					if (interview_data.job_opening) {
						frm._preserved_job_opening = interview_data.job_opening;
					}
					if (interview_data.demand) {
						frm._preserved_demand = interview_data.demand;
					}

					// Set interview_round (and interview_level) on doc FIRST so HRMS job_applicant handler does not throw "Select Interview Round First"
					if (interview_data.interview_round) {
						frm.doc.interview_round = interview_data.interview_round;
					}
					if (interview_data.interview_level) {
						frm.doc.interview_level = interview_data.interview_level;
					}
					if (interview_data.job_applicant) {
						frm.doc.job_applicant = interview_data.job_applicant;
					}
					if (interview_data.job_opening) {
						frm.doc.job_opening = interview_data.job_opening;
					}
					if (interview_data.demand) {
						try {
							frm.doc.demand = interview_data.demand;
						} catch (e) {
							// demand field may not exist in all HRMS versions
						}
					}

					setTimeout(function() {
						// Set interview_round first so HRMS job_applicant handler does not throw
						if (interview_data.interview_round && frm.fields_dict.interview_round) {
							safe_set_value(frm, "interview_round", interview_data.interview_round);
						}
						if (interview_data.interview_level && frm.fields_dict.interview_level) {
							safe_set_value(frm, "interview_level", interview_data.interview_level);
						}
						if (interview_data.job_applicant) {
							safe_set_value(frm, "job_applicant", interview_data.job_applicant);
						}
						if (interview_data.job_opening) {
							safe_set_value(frm, "job_opening", interview_data.job_opening);
						}
						if (interview_data.demand) {
							safe_set_value(frm, "demand", interview_data.demand);
						}
						frm._suppress_validation = false;

						if (frm.is_new() && interview_data.job_applicant) {
							frm._job_applicant_monitor = setInterval(function() {
								if (frm.doc.job_applicant !== interview_data.job_applicant && interview_data.job_applicant) {
									frm.doc.job_applicant = interview_data.job_applicant;
									safe_set_value(frm, "job_applicant", interview_data.job_applicant);
								}
								if (frm.doc.job_opening !== interview_data.job_opening && interview_data.job_opening) {
									frm.doc.job_opening = interview_data.job_opening;
									safe_set_value(frm, "job_opening", interview_data.job_opening);
								}
							}, 100);
							frm.script_manager.on("save", function() {
								if (frm._job_applicant_monitor) {
									clearInterval(frm._job_applicant_monitor);
									frm._job_applicant_monitor = null;
								}
							});
						}
					}, 200);
				} catch (e) {
					console.error("Error parsing interview data from session:", e);
					frm._suppress_validation = false;
				}
			} else {
				frm._suppress_validation = false;
			}
		}
	},

	refresh: function(frm) {
		// Keep Scheduled On editable (HRMS may set set_only_once / read_only)
		if (frm.fields_dict.scheduled_on) {
			frm.set_df_property("scheduled_on", "read_only", 0);
		}
		if (frm.is_new()) {
			// Default Scheduled On to today (required by HRMS); field remains editable
			if (!frm.doc.scheduled_on && frm.fields_dict.scheduled_on) {
				frm.set_value("scheduled_on", frappe.datetime.get_today());
			}
			const restore_values = function() {
				const stored_data = sessionStorage.getItem("interview_from_job_applicant") || sessionStorage.getItem("interview_from_application");
				if (stored_data) {
					try {
						const interview_data = JSON.parse(stored_data);
						if (interview_data.job_applicant && !frm.doc.job_applicant) {
							frm._preserved_job_applicant = interview_data.job_applicant;
							frm.doc.job_applicant = interview_data.job_applicant;
							safe_set_value(frm, "job_applicant", interview_data.job_applicant);
						}
						if (interview_data.job_opening && !frm.doc.job_opening) {
							frm._preserved_job_opening = interview_data.job_opening;
							frm.doc.job_opening = interview_data.job_opening;
							safe_set_value(frm, "job_opening", interview_data.job_opening);
						}
						if (interview_data.demand && !frm.doc.demand) {
							frm._preserved_demand = interview_data.demand;
							frm.doc.demand = interview_data.demand;
							safe_set_value(frm, "demand", interview_data.demand);
						}
					} catch (e) {
						console.error("Error restoring from sessionStorage:", e);
					}
				}

				if (frm._preserved_job_applicant && !frm.doc.job_applicant) {
					frm.doc.job_applicant = frm._preserved_job_applicant;
					safe_set_value(frm, "job_applicant", frm._preserved_job_applicant);
				}
				if (frm._preserved_job_opening && !frm.doc.job_opening) {
					frm.doc.job_opening = frm._preserved_job_opening;
					safe_set_value(frm, "job_opening", frm._preserved_job_opening);
				}
				if (frm._preserved_demand && !frm.doc.demand) {
					frm.doc.demand = frm._preserved_demand;
					safe_set_value(frm, "demand", frm._preserved_demand);
				}

				if (frm.doc.job_applicant && frm.fields_dict && frm.fields_dict.job_applicant) {
					frm.set_value("job_applicant", frm.doc.job_applicant);
				}
			};
			restore_values();
			setTimeout(restore_values, 100);
		}

		if (frm.doc.interview_start_time && frm.doc.interview_end_time) {
			calculate_total_time(frm);
		}

		// Pipeline Context: show Job Applicant's pipeline and current stage (read-only)
		if (frm.doc.job_applicant && frm.fields_dict.applicant_pipeline && frm.fields_dict.applicant_current_stage) {
			frappe.call({
				method: "recruitment_system.recruitment_system.doctype.job_applicant.job_applicant.get_job_applicant_pipeline_context",
				args: { job_applicant_name: frm.doc.job_applicant },
				callback: function(r) {
					if (r.message) {
						frm.set_value("applicant_pipeline", r.message.pipeline || "");
						frm.set_value("applicant_current_stage", r.message.current_stage_name || "");
					}
				}
			});
		} else if (frm.fields_dict.applicant_pipeline && frm.fields_dict.applicant_current_stage) {
			frm.set_value("applicant_pipeline", "");
			frm.set_value("applicant_current_stage", "");
		}
	},

	job_applicant: function(frm) {
		// Refresh pipeline context when Job Applicant changes
		if (frm.doc.job_applicant && frm.fields_dict.applicant_pipeline && frm.fields_dict.applicant_current_stage) {
			frappe.call({
				method: "recruitment_system.recruitment_system.doctype.job_applicant.job_applicant.get_job_applicant_pipeline_context",
				args: { job_applicant_name: frm.doc.job_applicant },
				callback: function(r) {
					if (r.message) {
						frm.set_value("applicant_pipeline", r.message.pipeline || "");
						frm.set_value("applicant_current_stage", r.message.current_stage_name || "");
					}
				}
			});
		}
	},

	interview_start_time: function(frm) {
		calculate_total_time(frm);
	},

	interview_end_time: function(frm) {
		calculate_total_time(frm);
	},

	interview_date: function(frm) {
		calculate_total_time(frm);
	},

	interview_round: function(frm) {
		if (frm.is_new()) {
			const saved_job_applicant = frm.doc.job_applicant || frm._preserved_job_applicant;
			const saved_job_opening = frm.doc.job_opening || frm._preserved_job_opening;
			const saved_demand = frm.doc.demand || frm._preserved_demand;

			const stored_data = sessionStorage.getItem("interview_from_job_applicant") || sessionStorage.getItem("interview_from_application");
			let session_job_applicant = saved_job_applicant;
			let session_job_opening = saved_job_opening;
			let session_demand = saved_demand;
			if (stored_data) {
				try {
					const interview_data = JSON.parse(stored_data);
					session_job_applicant = interview_data.job_applicant || saved_job_applicant;
					session_job_opening = interview_data.job_opening || saved_job_opening;
					session_demand = interview_data.demand || saved_demand;
				} catch (e) {
					console.error("Error parsing sessionStorage:", e);
				}
			}

			const final_job_applicant = session_job_applicant || saved_job_applicant;
			const final_job_opening = session_job_opening || saved_job_opening;
			const final_demand = session_demand || saved_demand;

			const restore_values = function() {
				let job_applicant = final_job_applicant || frm._preserved_job_applicant;
				let job_opening = final_job_opening || frm._preserved_job_opening;
				let demand = final_demand || frm._preserved_demand;

				const stored_data = sessionStorage.getItem("interview_from_job_applicant") || sessionStorage.getItem("interview_from_application");
				if (stored_data) {
					try {
						const interview_data = JSON.parse(stored_data);
						if (!job_applicant && interview_data.job_applicant) job_applicant = interview_data.job_applicant;
						if (!job_opening && interview_data.job_opening) job_opening = interview_data.job_opening;
						if (!demand && interview_data.demand) demand = interview_data.demand;
					} catch (e) {
						console.error("Error parsing sessionStorage:", e);
					}
				}

				if (job_applicant) {
					frm._preserved_job_applicant = job_applicant;
				}
				if (job_opening) {
					frm._preserved_job_opening = job_opening;
				}
				if (demand) {
					frm._preserved_demand = demand;
				}

				if (job_applicant) {
					frm.doc.job_applicant = job_applicant;
					if (frm.fields_dict && frm.fields_dict.job_applicant) {
						frm.set_value("job_applicant", job_applicant);
					}
				}
				if (job_opening) {
					frm.doc.job_opening = job_opening;
					if (frm.fields_dict && frm.fields_dict.job_opening) {
						frm.set_value("job_opening", job_opening);
					}
				}
				if (demand) {
					frm.doc.demand = demand;
					if (frm.fields_dict && frm.fields_dict.demand) {
						frm.set_value("demand", demand);
					}
				}
			};

			restore_values();
			setTimeout(restore_values, 0);
			setTimeout(restore_values, 10);
			setTimeout(restore_values, 50);
			setTimeout(restore_values, 200);
			setTimeout(function() {
				restore_values();

				if (frm.is_new() && final_job_applicant) {
					if (frm._job_applicant_monitor) {
						clearInterval(frm._job_applicant_monitor);
					}
					frm._job_applicant_monitor = setInterval(function() {
						const preserved_job_applicant = frm._preserved_job_applicant || final_job_applicant;
						const preserved_job_opening = frm._preserved_job_opening || final_job_opening;
						const preserved_demand = frm._preserved_demand || final_demand;

						if (preserved_job_applicant && frm.doc.job_applicant !== preserved_job_applicant) {
							frm.doc.job_applicant = preserved_job_applicant;
							safe_set_value(frm, "job_applicant", preserved_job_applicant);
						}
						if (preserved_job_opening && frm.doc.job_opening !== preserved_job_opening) {
							frm.doc.job_opening = preserved_job_opening;
							safe_set_value(frm, "job_opening", preserved_job_opening);
						}
						if (preserved_demand && frm.doc.demand !== preserved_demand) {
							frm.doc.demand = preserved_demand;
							safe_set_value(frm, "demand", preserved_demand);
						}
					}, 100);
					if (!frm._save_handler_added) {
						frm.script_manager.on("save", function() {
							if (frm._job_applicant_monitor) {
								clearInterval(frm._job_applicant_monitor);
								frm._job_applicant_monitor = null;
							}
						});
						frm._save_handler_added = true;
					}
				}

				if (frm.doc.job_applicant && frm.doc.job_opening) {
					sessionStorage.removeItem("interview_from_job_applicant");
					sessionStorage.removeItem("interview_from_application");
				}
			}, 500);
		}
	}
});

function safe_set_value(frm, fieldname, value) {
	try {
		if (frm.fields_dict && frm.fields_dict[fieldname]) {
			frm.set_value(fieldname, value);
			return true;
		}
		return false;
	} catch (e) {
		console.warn("Field '" + fieldname + "' not found or cannot be set:", e);
		return false;
	}
}

function calculate_total_time(frm) {
	if (!frm.doc.interview_start_time || !frm.doc.interview_end_time) {
		frm.set_value("total_time", "");
		return;
	}
	try {
		let start_time_str = frm.doc.interview_start_time;
		let end_time_str = frm.doc.interview_end_time;
		if (typeof start_time_str !== "string") {
			start_time_str = frappe.datetime.obj_to_str(start_time_str, "HH:mm:ss");
		}
		if (typeof end_time_str !== "string") {
			end_time_str = frappe.datetime.obj_to_str(end_time_str, "HH:mm:ss");
		}
		const start_parts = start_time_str.split(":");
		const end_parts = end_time_str.split(":");
		if (start_parts.length < 2 || end_parts.length < 2) {
			frm.set_value("total_time", "");
			return;
		}
		const start_hours = parseInt(start_parts[0], 10) || 0;
		const start_minutes = parseInt(start_parts[1], 10) || 0;
		const start_seconds = parseInt(start_parts[2] || 0, 10) || 0;
		const end_hours = parseInt(end_parts[0], 10) || 0;
		const end_minutes = parseInt(end_parts[1], 10) || 0;
		const end_seconds = parseInt(end_parts[2] || 0, 10) || 0;
		const start_total_seconds = start_hours * 3600 + start_minutes * 60 + start_seconds;
		const end_total_seconds = end_hours * 3600 + end_minutes * 60 + end_seconds;
		let diff_seconds = end_total_seconds - start_total_seconds;
		if (diff_seconds < 0) {
			diff_seconds += 24 * 3600;
		}
		if (diff_seconds <= 0) {
			frm.set_value("total_time", "");
			return;
		}
		const total_minutes = Math.floor(diff_seconds / 60);
		const hours = Math.floor(total_minutes / 60);
		const minutes = total_minutes % 60;
		let total_time_str = "";
		if (hours > 0 && minutes > 0) {
			total_time_str = hours + " hour" + (hours > 1 ? "s" : "") + " " + minutes + " minute" + (minutes > 1 ? "s" : "");
		} else if (hours > 0) {
			total_time_str = hours + " hour" + (hours > 1 ? "s" : "");
		} else if (minutes > 0) {
			total_time_str = minutes + " minute" + (minutes > 1 ? "s" : "");
		} else {
			const seconds = diff_seconds % 60;
			total_time_str = seconds + " second" + (seconds > 1 ? "s" : "");
		}
		frm.set_value("total_time", total_time_str);
	} catch (e) {
		console.error("Error calculating total time:", e);
		frappe.show_alert({
			indicator: "orange",
			message: __("Error calculating total time. Please check time values.")
		}, 3);
		frm.set_value("total_time", "");
	}
}
