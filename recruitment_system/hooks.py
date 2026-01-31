app_name = "recruitment_system"
app_title = "Recruitment System"
app_publisher = "abdullahjavaid198@gmail.com"
app_description = "Automating the recruitment system"
app_email = "abdullahjavaid198@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "recruitment_system",
# 		"logo": "/assets/recruitment_system/logo.png",
# 		"title": "Recruitment System",
# 		"route": "/recruitment_system",
# 		"has_permission": "recruitment_system.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/recruitment_system/css/recruitment_system.css"
# app_include_js = "/assets/recruitment_system/js/recruitment_system.js"

# include js, css files in header of web template
# web_include_css = "/assets/recruitment_system/css/recruitment_system.css"
# web_include_js = "/assets/recruitment_system/js/recruitment_system.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "recruitment_system/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Job Opening": "public/js/job_opening_demand.js",
	"Job Applicant": "public/js/job_applicant.js",
	"Interview": "public/js/interview.js"
}
# List view: bulk action "Create Bulk Interviews" for Job Applicant (same Demand and Demand Position)
doctype_list_js = {
	"Job Applicant": "public/js/job_applicant_list.js",
}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "recruitment_system/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "recruitment_system.utils.jinja_methods",
# 	"filters": "recruitment_system.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "recruitment_system.install.before_install"
after_install = "recruitment_system.install.after_install"
after_migrate = "recruitment_system.install.after_migrate"

# Uninstallation
# ------------

# before_uninstall = "recruitment_system.uninstall.before_uninstall"
# after_uninstall = "recruitment_system.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "recruitment_system.utils.before_app_install"
# after_app_install = "recruitment_system.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "recruitment_system.utils.before_app_uninstall"
# after_app_uninstall = "recruitment_system.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "recruitment_system.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
	"Job Opening": "recruitment_system.recruitment_system.doctype.job_opening_demand.job_opening.JobOpening",
	"Job Applicant": "recruitment_system.recruitment_system.doctype.job_applicant.job_applicant.JobApplicant",
	"Interview": "recruitment_system.recruitment_system.interview.interview.Interview"
}

# Document Events
# ---------------
# Hook on document methods and events
# Note: Demand Drive folder management hooks are implemented directly in Demand class
# (after_insert, on_update, on_trash methods are automatically called by Frappe)
# Job Applicant -> Visa Process stage sync: when JA is saved with pipeline "Visa Process",
# keep linked Visa Process's pipeline and current_stage in sync (works with HRMS controller).
doc_events = {
	"Job Applicant": {
		"on_update": "recruitment_system.recruitment_system.doctype.job_applicant.job_applicant.sync_job_applicant_stage_to_visa_process",
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"recruitment_system.tasks.all"
# 	],
# 	"daily": [
# 		"recruitment_system.tasks.daily"
# 	],
# 	"hourly": [
# 		"recruitment_system.tasks.hourly"
# 	],
# 	"weekly": [
# 		"recruitment_system.tasks.weekly"
# 	],
# 	"monthly": [
# 		"recruitment_system.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "recruitment_system.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "recruitment_system.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "recruitment_system.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["recruitment_system.utils.before_request"]
# after_request = ["recruitment_system.utils.after_request"]

# Job Events
# ----------
# before_job = ["recruitment_system.utils.before_job"]
# after_job = ["recruitment_system.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"recruitment_system.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

