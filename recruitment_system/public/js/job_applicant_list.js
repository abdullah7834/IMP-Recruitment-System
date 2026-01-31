// Copyright (c) 2026, Recruitment System
// Bulk Interview creation from Job Applicant list view (same Demand and Demand Position).

frappe.listview_settings["Job Applicant"] = {
	add_fields: ["status"],
	get_indicator: function (doc) {
		if (doc.status == "Accepted") {
			return [__(doc.status), "green", "status,=," + doc.status];
		} else if (["Open", "Replied"].includes(doc.status)) {
			return [__(doc.status), "orange", "status,=," + doc.status];
		} else if (["Hold", "Rejected"].includes(doc.status)) {
			return [__(doc.status), "red", "status,=," + doc.status];
		}
	},
	onload: function (list_view) {
		list_view.page.add_inner_button(__("Create Bulk Interviews"), function () {
			const docnames = list_view.get_checked_items(true);
			if (!docnames || docnames.length === 0) {
				frappe.msgprint({
					title: __("Selection Required"),
					message: __("Please select at least one Job Applicant from the list."),
					indicator: "orange",
				});
				return;
			}
			frappe.call({
				method: "recruitment_system.recruitment_system.interview.bulk.get_bulk_interview_selection_context",
				args: { job_applicant_names: docnames },
				freeze: true,
				freeze_message: __("Validating selection..."),
				callback: function (r) {
					if (r.exc) {
						return;
					}
					const ctx = r.message;
					if (!ctx || !ctx.job_applicants || ctx.job_applicants.length === 0) {
						frappe.msgprint({ title: __("Error"), message: __("No valid Job Applicants."), indicator: "red" });
						return;
					}
					open_bulk_interview_dialog(ctx, list_view);
				},
			});
		});
	},
};

function open_bulk_interview_dialog(context, list_view) {
	const d = new frappe.ui.Dialog({
		title: __("Create Bulk Interviews"),
		fields: [
			{
				fieldtype: "Read Only",
				label: __("Demand"),
				fieldname: "demand",
				default: context.demand || "",
			},
			{
				fieldtype: "Read Only",
				label: __("Demand Position"),
				fieldname: "demand_position",
				default: context.demand_position || "",
			},
			{
				fieldtype: "Read Only",
				label: __("Candidates"),
				fieldname: "count",
				default: __("{0} Job Applicant(s) selected", [context.count]),
			},
			{ fieldtype: "Section Break" },
			{
				fieldtype: "Link",
				label: __("Interview Round"),
				fieldname: "interview_round",
				options: "Interview Round",
				reqd: 1,
			},
			{
				fieldtype: "Date",
				label: __("Interview Date"),
				fieldname: "interview_date",
				reqd: 1,
				default: frappe.datetime.get_today(),
			},
			{
				fieldtype: "Time",
				label: __("From Time"),
				fieldname: "from_time",
			},
			{
				fieldtype: "Time",
				label: __("To Time"),
				fieldname: "to_time",
			},
		],
		primary_action_label: __("Create Interviews"),
		primary_action: function () {
			const values = d.get_values();
			if (!values || !values.interview_round || !values.interview_date) {
				frappe.msgprint({ title: __("Required"), message: __("Interview Round and Interview Date are required."), indicator: "orange" });
				return;
			}
			d.hide();
			frappe.call({
				method: "recruitment_system.recruitment_system.interview.bulk.create_bulk_interviews",
				args: {
					job_applicants: context.job_applicants,
					interview_round: values.interview_round,
					interview_date: values.interview_date,
					start_time: values.from_time || undefined,
					end_time: values.to_time || undefined,
				},
				freeze: true,
				freeze_message: __("Creating Interviews..."),
				callback: function (r) {
					if (r.exc) return;
					const result = r.message;
					if (result && result.created_count !== undefined) {
						frappe.msgprint({
							title: __("Bulk Interviews"),
							message: __("Created {0} Interview(s).", [result.created_count]) +
								(result.failed_count ? " " + __("Failed: {0}", [result.failed_count]) : ""),
							indicator: result.failed_count ? "orange" : "green",
						});
						list_view.clear_checked_items();
						list_view.refresh();
					}
				},
			});
		},
	});
	d.show();
}
