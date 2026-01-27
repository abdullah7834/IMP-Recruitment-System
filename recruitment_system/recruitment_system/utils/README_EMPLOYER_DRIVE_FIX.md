# Employer Drive Folder Fix Utility

## Problem
If you see an empty `/Employers/` folder in Frappe Drive, it means the employer-specific folders were not created when the Employer records were created.

## Solution

### Option 1: Fix via Console (Recommended)

1. Open Frappe console:
```bash
bench --site [your-site-name] console
```

2. Run the fix script:
```python
from recruitment_system.recruitment_system.recruitment_system.utils.employer_drive_fix import fix_all_employers

# Fix all existing Employers
result = fix_all_employers()
print(f"Total: {result['total']}, Success: {result['success']}, Failed: {result['failed']}")
if result['errors']:
    print("Errors:", result['errors'])
```

### Option 2: Fix Single Employer via Console

```python
from recruitment_system.recruitment_system.recruitment_system.utils.employer_drive_fix import fix_single_employer

# Fix a specific Employer by name or ID
result = fix_single_employer("Employer Name or ID")
print(result)
```

### Option 3: Fix via API (from UI)

1. Open any Employer record in Frappe
2. In the browser console, run:
```javascript
frappe.call({
    method: 'recruitment_system.recruitment_system.recruitment_system.utils.employer_drive_fix.fix_single_employer',
    args: {
        employer_name: 'YOUR_EMPLOYER_NAME_OR_ID'
    },
    callback: function(r) {
        frappe.show_alert(r.message);
    }
});
```

### Option 4: Use Whitelisted Method on Employer Document

1. Open an Employer record
2. In the browser console, run:
```javascript
frappe.call({
    method: 'recruitment_system.recruitment_system.recruitment_system.doctype.employer.employer.create_drive_folders',
    args: {
        name: 'EMPLOYER_ID'  // Replace with actual Employer ID
    },
    callback: function(r) {
        frappe.show_alert(r.message);
    }
});
```

## What Gets Created

When you run the fix, it will create the following folder structure for each Employer:

```
/Employers/{Employer Name}/
   /Legal/
      /MOU/
      /POA/
      /Contracts/
      /Licenses/
   /Demands/
   /Job_Openings/
   /Batches/
```

## Troubleshooting

### If folders still don't appear:

1. **Check Error Log**: Go to `Error Log` in Frappe and look for "Employer Drive Folder Creation Error"

2. **Verify Drive Team**: Make sure you have a Drive Team set up:
   - Go to Drive app
   - Check if you have a personal team or are a member of a team

3. **Check Employer Name**: Ensure the Employer record has an `employer_name` field filled

4. **Manual Check**: Verify the folder was created:
```python
import frappe
from drive.utils import get_home_folder

team = frappe.db.get_value("Drive Team", {"owner": frappe.session.user, "personal": 1}, "name")
if team:
    home_folder = get_home_folder(team)
    employers_root = frappe.db.get_value(
        "Drive File",
        {"title": "Employers", "parent_entity": home_folder.name, "is_group": 1, "is_active": 1},
        "name"
    )
    if employers_root:
        print(f"Employers root folder: {employers_root}")
        # List all employer folders
        employer_folders = frappe.get_all(
            "Drive File",
            filters={"parent_entity": employers_root, "is_group": 1, "is_active": 1},
            fields=["name", "title"]
        )
        print(f"Employer folders: {employer_folders}")
```

## Prevention

Going forward, folders will be automatically created when:
- A new Employer is created (via `after_insert` hook)
- An Employer is updated and folder structure is missing (via `on_update` hook)

The system is idempotent - it won't create duplicate folders if they already exist.
