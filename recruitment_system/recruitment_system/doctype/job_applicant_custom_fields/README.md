# Job Applicant Custom Fields

This module adds minimal, clean custom fields to the standard `Job Applicant` DocType from Frappe HR for overseas recruitment support.

## Purpose

The custom fields transform `Job Applicant` into:
- An application intake & screening layer
- A bridge between Applicant (master) and Application (pipeline)

## Fields Added

### 1. Applicant Reference Section
- **applicant** (Link to Applicant) - Mandatory link to CNIC-based Applicant master

### 2. Demand Context Section
- **linked_demand** (Link to Demand) - Optional link to Demand
- **demand_position** (Data) - Optional demand position

### 3. Screening Results Section
- **internal_hr_result** (Select: Pass/Fail/Hold) - Internal HR screening result
- **technical_result** (Select: Pass/Fail/Hold) - Technical interview result

### 4. Pipeline Bridge (Control) Section
- **ready_for_pipeline** (Check) - Gatekeeper flag before creating Application
- **converted_to_application** (Check, Read Only) - Prevents duplicate Application creation

## Usage

### Method 1: Via Console (Recommended)

```python
# In Frappe console (bench console)
from recruitment_system.recruitment_system.doctype.job_applicant_custom_fields.add_custom_fields import add_custom_fields_to_job_applicant

# Add custom fields
result = add_custom_fields_to_job_applicant()
print(result)
```

### Method 2: Via API

```python
# Via API call
frappe.call("recruitment_system.recruitment_system.doctype.job_applicant_custom_fields.add_custom_fields.add_custom_fields_to_job_applicant")
```

### Method 3: Check Existing Fields

```python
# Check what fields exist
from recruitment_system.recruitment_system.doctype.job_applicant_custom_fields.add_custom_fields import get_job_applicant_existing_fields

result = get_job_applicant_existing_fields()
print(result)
```

### Method 4: Clean Up Duplicates

```python
# Remove duplicate custom fields
from recruitment_system.recruitment_system.doctype.job_applicant_custom_fields.add_custom_fields import cleanup_duplicate_job_applicant_custom_fields

result = cleanup_duplicate_job_applicant_custom_fields()
print(result)
```

## Design Principles

✅ **DO:**
- Keep fields minimal and semantic
- Use 2 fields per row for clean UI
- Link to Applicant master (no duplication)
- Use clear section breaks

❌ **DON'T:**
- Duplicate Applicant master data
- Add visa, batch, or deployment fields
- Add complex workflow logic
- Override existing HRMS fields
- Use generic fieldnames (column_break_1 style)

## Field Layout

```
Job Applicant Form:
├── [Standard HRMS Fields]
├── Applicant Reference Section
│   └── Applicant (Master) *
├── Demand Context Section
│   ├── Linked Demand | Demand Position
├── Screening Results Section
│   ├── Internal HR Result | Technical Result
└── Pipeline Bridge (Control) Section
    ├── Ready for Application Pipeline | Converted to Application
```

## Notes

- All fieldnames are semantic and unique
- No duplicate Column Break names
- Fields are upgrade-safe
- Standard HRMS fields are preserved
- Custom fields can be removed/re-added safely

## Troubleshooting

If you encounter "Fieldname appears multiple times" error:

```python
# Clean up duplicates
cleanup_duplicate_job_applicant_custom_fields()

# Then re-add fields
add_custom_fields_to_job_applicant()
```
