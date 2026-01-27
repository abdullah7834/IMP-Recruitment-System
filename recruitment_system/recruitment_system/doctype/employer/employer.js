// Copyright (c) 2026, abdullahjavaid198@gmail.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employer", {
	refresh(frm) {
		// Show warning if force_delete is not checked
		if (frm.doc.force_delete) {
			frm.dashboard.add_indicator(__("Deletion Enabled"), "orange");
		}
	},
});

// Custom delete handler for list view
frappe.listview_settings["Employer"] = {
	onload: function(listview) {
		// Override delete to show helpful message
		listview.page.add_inner_button(__("Delete with Drive Cleanup"), function() {
			const selected_docs = listview.get_checked_items();
			if (selected_docs.length === 0) {
				frappe.msgprint(__("Please select at least one Employer to delete."));
				return;
			}
			
			frappe.confirm(
				__("This will delete the selected Employer(s) and their Drive folders. This action cannot be undone. Do you want to continue?"),
				function() {
					// Yes - proceed with deletion
					frappe.call({
						method: "frappe.client.delete",
						args: {
							doctype: "Employer",
							name: selected_docs[0].name,
							force: 0
						},
						callback: function(r) {
							if (r.exc) {
								// If deletion fails, show helpful message
								if (r.exc.includes("Deletion Blocked") || r.exc.includes("force_delete")) {
									frappe.msgprint({
										title: __("Deletion Blocked"),
										message: __("Please open the Employer record, check the 'Allow Deletion (Delete Drive Folders)' checkbox, save the record, then try deleting again."),
										indicator: "orange"
									});
								} else {
									frappe.msgprint({
										title: __("Error"),
										message: r.exc,
										indicator: "red"
									});
								}
							} else {
								listview.refresh();
							}
						}
					});
				}
			);
		}, __("Actions"));
	}
};
