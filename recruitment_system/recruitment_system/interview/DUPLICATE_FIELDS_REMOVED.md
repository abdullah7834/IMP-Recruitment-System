# Duplicate Fields Removed from Interview DocType

## Summary
Removed duplicate custom fields that conflicted with standard HRMS Interview fields.

## Fields Removed

### 1. **job_opening** (Custom Field)
- **Status**: ❌ REMOVED
- **Reason**: Standard HRMS field already exists
- **Action**: Use standard `job_opening` field instead
- **Auto-population**: Handled via `auto_populate_from_job_applicant()` in `interview.py`

### 2. **demand** (Custom Field)
- **Status**: ❌ REMOVED
- **Reason**: Standard HRMS field already exists
- **Action**: Use standard `demand` field instead
- **Auto-population**: Handled via `auto_populate_from_job_applicant()` in `interview.py`

### 3. **interview_start_time** (Time Field - if exists)
- **Status**: ❌ REMOVED (if found)
- **Reason**: Duplicate of `interview_start` (Datetime field)
- **Action**: Use `interview_start` (Datetime) instead, which combines date and time

### 4. **interview_end_time** (Time Field - if exists)
- **Status**: ❌ REMOVED (if found)
- **Reason**: Duplicate of `interview_end` (Datetime field)
- **Action**: Use `interview_end` (Datetime) instead, which combines date and time

## Standard HRMS Fields (DO NOT ADD AS CUSTOM)

These fields already exist in HRMS Interview doctype:
- `job_applicant` - Link to Job Applicant
- `interview_round` - Link to Interview Round
- `job_opening` - Link to Job Opening (standard HRMS)
- `demand` - Link to Demand (standard HRMS)
- `interview_date` - Date field
- `interview_time` - Time field
- `from_time` - Time field (standard HRMS)
- `to_time` - Time field (standard HRMS)
- `scheduled_on` - Date field (standard HRMS)
- `status` - Select field
- `result` - Select field

## Custom Fields Added (Non-Duplicate)

Application doctype was removed; Interview links only to Job Applicant. Custom fields that should exist:
1. `interview_level` - Select (Internal/Company)
2. `interview_type` - Select (HR/Technical/Trade/Company)
3. `interview_start_time` / `interview_end_time` - Time fields
4. `total_time` - Data (auto-calculated, read-only)
5. `interview_result` - Select (Pass/Fail/Hold)
6. `interviewer_notes` - Text

The obsolete `application` custom field is removed by `remove_application_field_from_interview()` / `remove_duplicate_interview_fields()`.

## How to Clean Up Existing Duplicates

Run this command in Frappe console:

```python
from recruitment_system.recruitment_system.interview.custom_fields import remove_duplicate_interview_fields

result = remove_duplicate_interview_fields()
print(result)
```

Then re-add custom fields:

```python
from recruitment_system.recruitment_system.interview.custom_fields import add_custom_fields_to_interview

result = add_custom_fields_to_interview()
print(result)
```

## Notes

- Standard HRMS fields (`job_opening`, `demand`) are automatically populated from Job Applicant via Python logic
- Application doctype was removed; do not add an `application` field to Interview
- All duplicate/obsolete fields are removed by `remove_duplicate_interview_fields()` before adding custom fields
