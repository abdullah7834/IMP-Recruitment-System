# Job Applicant Auto-Fetch Setup Instructions

## Step 1: Add Custom Fields (If Not Already Added)

Run this in Frappe console:

```bash
bench console
```

Then in the console:

```python
from recruitment_system.recruitment_system.doctype.job_applicant_custom_fields.add_custom_fields import add_custom_fields_to_job_applicant

result = add_custom_fields_to_job_applicant()
print(result)
```

Expected output:
```
{'success': True, 'added': X, 'skipped': Y, ...}
```

## Step 2: Restart Bench

```bash
bench restart
```

This will:
- Load the new JavaScript file
- Register the hooks
- Make the server-side method available

## Step 3: Clear Browser Cache

1. Open your browser's Developer Tools (F12)
2. Right-click on the refresh button
3. Select "Empty Cache and Hard Reload"
   
OR

1. Press `Ctrl + Shift + Delete` (Windows/Linux)
2. Select "Cached images and files"
3. Click "Clear data"

## Step 4: Test the Functionality

1. Open a Job Applicant form (new or existing)
2. Open Browser Console (F12 → Console tab)
3. Select an Applicant from "Applicant (Master)" dropdown
4. You should see:
   - Console logs: `[Job Applicant] applicant field changed: ...`
   - Console logs: `[Job Applicant] Fetching details for applicant: ...`
   - Console logs: `[Job Applicant] Server response: ...`
   - Fields auto-populate: Applicant Name, Email Address, Phone Number
   - Success message appears

## Step 5: Verify JavaScript is Loaded

In Browser Console, check if the file is loaded:

```javascript
// Check if the handler is registered
console.log(frappe.ui.form.on);
```

## Step 6: Test Server Method Directly

In Frappe console:

```python
from recruitment_system.recruitment_system.doctype.job_applicant_custom_fields.add_custom_fields import get_applicant_details

# Replace with an actual Applicant CNIC/name
result = get_applicant_details("1234567890123")
print(result)
```

Expected output:
```
{'full_name': 'John Doe', 'email_address': 'john@example.com', 'mobile_number': '1234567890'}
```

## Troubleshooting

### Issue: Fields Not Auto-Populating

1. **Check Browser Console for Errors:**
   - Open F12 → Console
   - Look for red error messages
   - Check if method path is correct

2. **Verify Custom Fields Exist:**
   ```python
   # In Frappe console
   from recruitment_system.recruitment_system.doctype.job_applicant_custom_fields.add_custom_fields import get_job_applicant_existing_fields
   result = get_job_applicant_existing_fields()
   print(result)
   ```
   - Check if `applicant` field exists in custom_fields list

3. **Check JavaScript File is Loaded:**
   - Open Browser → Network tab
   - Reload Job Applicant form
   - Look for `job_applicant.js` in the network requests
   - Status should be 200 (not 404)

4. **Verify Hooks:**
   ```python
   # In Frappe console
   import frappe
   hooks = frappe.get_hooks("doctype_js")
   print(hooks.get("Job Applicant"))
   ```
   Should output: `['public/js/job_applicant.js']`

### Issue: Method Not Found Error

If you see "Method not found" error:

1. **Check Method Path:**
   - The method is in: `add_custom_fields.py`
   - Path should be: `recruitment_system.recruitment_system.doctype.job_applicant_custom_fields.add_custom_fields.get_applicant_details`

2. **Verify Method is Whitelisted:**
   - Check that `@frappe.whitelist()` decorator is present
   - Method name is `get_applicant_details`

3. **Restart Bench Again:**
   ```bash
   bench restart
   ```

### Issue: No Console Logs Appearing

1. **Check if JavaScript is Registered:**
   - Open Browser Console
   - Type: `frappe.ui.form.on`
   - Should show the function, not undefined

2. **Check Field Name:**
   - Verify the custom field is named exactly `applicant`
   - Check in Customize Form → Job Applicant → Fields

3. **Manual Test:**
   ```javascript
   // In Browser Console on Job Applicant form
   frappe.ui.form.on("Job Applicant", {
       applicant: function(frm) {
           console.log("TEST: Applicant field changed!", frm.doc.applicant);
       }
   });
   ```
   Then change the applicant field - you should see the log

## Quick Verification Commands

```bash
# 1. Check if JavaScript file exists
ls -la apps/recruitment_system/recruitment_system/recruitment_system/public/js/job_applicant.js

# 2. Check hooks.py
grep -A 2 "Job Applicant" apps/recruitment_system/recruitment_system/hooks.py

# 3. Check method exists
grep "get_applicant_details" apps/recruitment_system/recruitment_system/recruitment_system/doctype/job_applicant_custom_fields/add_custom_fields.py

# 4. Restart bench
bench restart
```

## Expected Behavior

When you select an Applicant:
1. ✅ Console shows: `[Job Applicant] applicant field changed: [CNIC]`
2. ✅ Console shows: `[Job Applicant] Fetching details for applicant: [CNIC]`
3. ✅ Console shows: `[Job Applicant] Server response: {message: {...}}`
4. ✅ Fields auto-populate (if empty)
5. ✅ Success message appears: "Fetched and populated: Applicant Name, Email Address, Phone Number"
