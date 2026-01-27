# Copyright (c) 2026, abdullahjavaid198@gmail.com and contributors
# For license information, please see license.txt
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


@frappe.whitelist()
def get_job_opening_existing_fields():
    """
    Get all existing fields in Job Opening doctype (both standard and custom).
    Use this to understand which fields already exist before adding custom fields.
    """
    try:
        # Get standard fields from DocType
        meta = frappe.get_meta("Job Opening")
        standard_fields = []
        for field in meta.fields:
            standard_fields.append({
                "fieldname": field.fieldname,
                "fieldtype": field.fieldtype,
                "label": field.label or "",
                "is_custom": 0
            })
        
        # Get custom fields
        custom_fields = frappe.get_all(
            "Custom Field",
            filters={"dt": "Job Opening"},
            fields=["name", "fieldname", "fieldtype", "label", "insert_after", "creation"],
            order_by="creation asc"
        )
        
        # Check for duplicates in custom fields
        fieldname_count = {}
        duplicates = []
        for cf in custom_fields:
            fn = cf.get("fieldname")
            if fn in fieldname_count:
                fieldname_count[fn] += 1
                duplicates.append(fn)
            else:
                fieldname_count[fn] = 1
        
        result = {
            "standard_fields": standard_fields,
            "custom_fields": custom_fields,
            "standard_field_count": len(standard_fields),
            "custom_field_count": len(custom_fields),
            "duplicates": list(set(duplicates))
        }
        
        # Print summary
        print("\n=== JOB OPENING FIELD SUMMARY ===")
        print(f"Standard fields: {len(standard_fields)}")
        print(f"Custom fields: {len(custom_fields)}")
        if duplicates:
            print(f"DUPLICATES FOUND: {list(set(duplicates))}")
        
        print("\n--- Standard Fields ---")
        for f in standard_fields:
            print(f"  {f['fieldname']} ({f['fieldtype']})")
        
        print("\n--- Custom Fields ---")
        for f in custom_fields:
            print(f"  {f['fieldname']} ({f['fieldtype']}) - name: {f['name']}")
        
        return result
        
    except Exception as e:
        frappe.log_error(f"Error getting Job Opening fields: {str(e)}", "Get Fields Error")
        return {"error": str(e)}


def check_field_exists(fieldname):
    """
    Check if a field already exists in Job Opening (either standard or custom)
    Returns True if field exists, False otherwise
    """
    try:
        meta = frappe.get_meta("Job Opening")
        # Check standard fields
        for field in meta.fields:
            if field.fieldname == fieldname:
                return True
        
        # Check custom fields
        if frappe.db.exists("Custom Field", {"dt": "Job Opening", "fieldname": fieldname}):
            return True
        
        return False
    except:
        return False


@frappe.whitelist()
def add_custom_fields_to_job_opening():
    """
    Add custom fields to Job Opening doctype for Demand integration.
    This function automatically excludes fields that already exist in the standard form.
    """
    # Standard fields that already exist - DO NOT add these as custom fields
    existing_standard_fields = [
        "status",           # Standard Select field with "Open\nClosed"
        "designation",      # Standard Link field to Designation
        "closes_on",        # Standard Date field
        "posted_on",        # Standard Datetime field
        "column_break_5"    # Standard Column Break
    ]
    
    custom_fields = {
        "Job Opening": [
            # Demand Information Section
            {
                "fieldname": "demand_section",
                "fieldtype": "Section Break",
                "label": "Demand Information",
                "insert_after": "job_title"
            },
            # Row 1: Linked Demand and Demand Position (side by side)
            {
                "fieldname": "linked_demand",
                "fieldtype": "Link",
                "label": "Linked Demand",
                "options": "Demand",
                "reqd": 1,
                "insert_after": "demand_section"
            },
            {
                "fieldname": "column_break_1",
                "fieldtype": "Column Break",
                "insert_after": "linked_demand"
            },
            {
                "fieldname": "demand_position",
                "fieldtype": "Select",
                "label": "Demand Position",
                "reqd": 1,
                "insert_after": "column_break_1"
            },
            # Row 2: Experience Required and Education Required (side by side)
            {
                "fieldname": "section_break_1",
                "fieldtype": "Section Break",
                "insert_after": "demand_position"
            },
            {
                "fieldname": "experience_required",
                "fieldtype": "Data",
                "label": "Experience Required",
                "insert_after": "section_break_1"
            },
            {
                "fieldname": "column_break_2",
                "fieldtype": "Column Break",
                "insert_after": "experience_required"
            },
            {
                "fieldname": "education_required",
                "fieldtype": "Data",
                "label": "Education Required",
                "insert_after": "column_break_2"
            },
            
            # Age Requirements Section
            {
                "fieldname": "age_section",
                "fieldtype": "Section Break",
                "label": "Age Requirements",
                "insert_after": "education_required"
            },
            # Row 1: Age Min and Age Max (side by side)
            {
                "fieldname": "age_min",
                "fieldtype": "Int",
                "label": "Age Min",
                "insert_after": "age_section"
            },
            {
                "fieldname": "column_break_3",
                "fieldtype": "Column Break",
                "insert_after": "age_min"
            },
            {
                "fieldname": "age_max",
                "fieldtype": "Int",
                "label": "Age Max",
                "insert_after": "column_break_3"
            },
            # Interview Requirements Section (Checkboxes)
            {
                "fieldname": "section_break_3",
                "fieldtype": "Section Break",
                "label": "Interview Requirements",
                "insert_after": "age_max"
            },
            {
                "fieldname": "internal_hr_required",
                "fieldtype": "Check",
                "label": "Internal HR Required",
                "default": 0,
                "insert_after": "section_break_3"
            },
            {
                "fieldname": "column_break_interview_1",
                "fieldtype": "Column Break",
                "insert_after": "internal_hr_required"
            },
            {
                "fieldname": "technical_interview_required",
                "fieldtype": "Check",
                "label": "Technical Interview Required",
                "default": 0,
                "insert_after": "column_break_interview_1"
            },
            {
                "fieldname": "column_break_interview_2",
                "fieldtype": "Column Break",
                "insert_after": "technical_interview_required"
            },
            {
                "fieldname": "trade_test_required",
                "fieldtype": "Check",
                "label": "Trade Test Required",
                "default": 0,
                "insert_after": "column_break_interview_2"
            }
        ]
    }
    
    try:
        # First, remove any existing custom fields to avoid duplicates
        remove_existing_custom_fields()
        
        # Filter out fields that already exist (standard or custom)
        fields_to_add = []
        skipped_fields = []
        
        for field in custom_fields["Job Opening"]:
            fieldname = field.get("fieldname")
            
            # Skip if it's in the list of existing standard fields
            if fieldname in existing_standard_fields:
                skipped_fields.append(f"{fieldname} (standard field)")
                continue
            
            # Skip if field already exists
            if check_field_exists(fieldname):
                skipped_fields.append(f"{fieldname} (already exists)")
                continue
            
            fields_to_add.append(field)
        
        # Only create fields that don't exist
        if fields_to_add:
            custom_fields["Job Opening"] = fields_to_add
            create_custom_fields(custom_fields, ignore_validate=True, update=True)
            
            message = f"Custom fields added successfully! Added {len(fields_to_add)} field(s)."
            if skipped_fields:
                message += f"\nSkipped {len(skipped_fields)} field(s) that already exist: {', '.join(skipped_fields)}"
            frappe.msgprint(message, title="Success")
        else:
            frappe.msgprint("No new custom fields to add. All fields already exist.", title="Info")
        
        return True
    except Exception as e:
        error_msg = f"Error adding custom fields: {str(e)}\n{frappe.get_traceback()}"
        frappe.log_error(error_msg, "Job Opening Custom Fields Error")
        frappe.msgprint(f"Error adding custom fields: {str(e)}")
        return False


def remove_existing_custom_fields():
    """
    Remove existing custom fields from Job Opening doctype to avoid duplicates
    """
    # List of all custom field names that might exist (including old names)
    # NOTE: designation, status, closes_on, posted_on are standard fields - don't add them as custom fields
    field_names = [
        # Current custom fields only
        "demand_section", "linked_demand", "column_break_1", "demand_position",
        "section_break_1", "experience_required", "column_break_2", "education_required",
        "age_section", "age_min", "column_break_3", "age_max",
        "section_break_3", "internal_hr_required", 
        "column_break_interview_1", "technical_interview_required", 
        "column_break_interview_2", "trade_test_required",
        # Old field names that might exist from previous versions (to clean up)
        "section_break_2", "column_break_4", "custom_status", "designation",
        "section_break_4", "posted_on", "column_break_dates", "closes_on",
        "column_break_5", "column_break_6", "column_break_7", "section_break_5",
        "demand_col_break", "requirements_section", "requirements_col_break",
        "job_details_section", "job_details_col_break", "interview_section",
        "dates_section", "dates_col_break"
    ]
    
    try:
        for field_name in field_names:
            custom_field_name = f"Job Opening-{field_name}"
            if frappe.db.exists("Custom Field", custom_field_name):
                frappe.delete_doc("Custom Field", custom_field_name, force=True, ignore_permissions=True)
        
        frappe.db.commit()
    except Exception as e:
        frappe.log_error(
            f"Error removing existing custom fields: {str(e)}\n{frappe.get_traceback()}",
            "Job Opening Custom Fields Cleanup Error"
        )
        # Don't throw error, just log it - we'll try to create anyway


@frappe.whitelist()
def cleanup_duplicate_custom_fields():
    """
    Remove ALL duplicate custom fields from Job Opening doctype.
    This function finds duplicates by fieldname and keeps only the first one.
    Use this when you get "Fieldname X appears multiple times" errors.
    """
    try:
        # Get all custom fields for Job Opening
        all_custom_fields = frappe.get_all(
            "Custom Field",
            filters={"dt": "Job Opening"},
            fields=["name", "fieldname", "creation"],
            order_by="creation asc"
        )
        
        if not all_custom_fields:
            frappe.msgprint("No custom fields found for Job Opening.")
            return {"status": "success", "message": "No custom fields to clean up"}
        
        # Group by fieldname to find duplicates
        fieldname_groups = {}
        for field in all_custom_fields:
            fieldname = field.get("fieldname")
            if fieldname not in fieldname_groups:
                fieldname_groups[fieldname] = []
            fieldname_groups[fieldname].append(field)
        
        # Find and remove duplicates (keep the first one, delete the rest)
        duplicates_found = []
        duplicates_removed = []
        
        for fieldname, fields in fieldname_groups.items():
            if len(fields) > 1:
                duplicates_found.append(fieldname)
                # Keep the first one (oldest by creation), delete the rest
                fields_to_delete = fields[1:]  # All except the first
                for field in fields_to_delete:
                    try:
                        frappe.delete_doc("Custom Field", field["name"], force=True, ignore_permissions=True)
                        duplicates_removed.append(f"{fieldname} (name: {field['name']})")
                    except Exception as e:
                        frappe.log_error(
                            f"Error deleting duplicate field {field['name']}: {str(e)}",
                            "Custom Field Cleanup Error"
                        )
        
        frappe.db.commit()
        
        if duplicates_found:
            message = f"Found {len(duplicates_found)} duplicate fieldname(s): {', '.join(duplicates_found)}\n"
            message += f"Removed {len(duplicates_removed)} duplicate field(s)."
            frappe.msgprint(message, title="Duplicate Fields Cleaned")
            return {
                "status": "success",
                "duplicates_found": duplicates_found,
                "duplicates_removed": duplicates_removed
            }
        else:
            frappe.msgprint("No duplicate fields found. All custom fields are unique.")
            return {"status": "success", "message": "No duplicates found"}
            
    except Exception as e:
        error_msg = f"Error cleaning up duplicate custom fields: {str(e)}\n{frappe.get_traceback()}"
        frappe.log_error(error_msg, "Job Opening Custom Fields Cleanup Error")
        frappe.msgprint(f"Error cleaning up duplicates: {str(e)}", title="Error")
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def remove_all_job_opening_custom_fields():
    """
    Remove ALL custom fields from Job Opening doctype.
    Use this to completely clean up before re-adding fields.
    """
    try:
        # Get all custom fields for Job Opening
        all_custom_fields = frappe.get_all(
            "Custom Field",
            filters={"dt": "Job Opening"},
            fields=["name", "fieldname"]
        )
        
        if not all_custom_fields:
            frappe.msgprint("No custom fields found for Job Opening.")
            return {"status": "success", "message": "No custom fields to remove"}
        
        removed_count = 0
        for field in all_custom_fields:
            try:
                frappe.delete_doc("Custom Field", field["name"], force=True, ignore_permissions=True)
                removed_count += 1
            except Exception as e:
                frappe.log_error(
                    f"Error deleting field {field['name']}: {str(e)}",
                    "Custom Field Removal Error"
                )
        
        frappe.db.commit()
        frappe.msgprint(f"Removed {removed_count} custom field(s) from Job Opening.", title="Success")
        return {"status": "success", "removed_count": removed_count}
        
    except Exception as e:
        error_msg = f"Error removing custom fields: {str(e)}\n{frappe.get_traceback()}"
        frappe.log_error(error_msg, "Job Opening Custom Fields Removal Error")
        frappe.msgprint(f"Error removing custom fields: {str(e)}", title="Error")
        return {"status": "error", "message": str(e)}