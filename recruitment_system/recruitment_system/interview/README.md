# Interview Module

Extends HRMS Interview module for overseas recruitment workflows while keeping HRMS functionality intact.

## Overview

This module adds custom fields and logic to the built-in HRMS Interview DocType without breaking existing HRMS functionality. Interview Type comes from Interview Round (HRMS built-in).

## Custom Fields Added

### Timing Section
- **interview_start_time** (Time) - Interview start time
- **interview_end_time** (Time) - Interview end time  
- **interview_duration_minutes** (Int, Read Only) - Auto-calculated duration

### Result Section
- **interview_result** (Select) - Interview result: Pass/Fail/Hold
- **interviewer_notes** (Text) - Interviewer notes and feedback

## Automation Logic

### On Interview Save

1. **Duration Calculation**: Automatically calculates total time from start and end times
2. **Job Applicant Sync**: Syncs Interview result to Job Applicant pipeline/stage:
   - **Internal HR/Technical Interviews**:
     - Pass → Job Applicant stage = "Internally Selected"
     - Fail → Job Applicant stage = "Internal Rejected"
   - **Company Interviews**:
     - Pass → Job Applicant stage = "Company Selected", then moves to Offer Letter pipeline
     - Fail → Job Applicant stage = "Company Rejected"

3. **Validation**:
   - Blocks Company Interview if Internal Interview hasn't passed
   - Blocks Interview if Job Applicant is in terminal stages (Rejected/Deployed)
   - job_opening and demand are auto-populated from Job Applicant

## Bulk Interview Creation

### Usage

```python
from recruitment_system.recruitment_system.interview.bulk import create_bulk_interviews

result = create_bulk_interviews(
    interview_round="Internal HR",
    interview_date="2026-02-01",
    start_time="09:00:00",
    end_time="10:00:00",
    job_applicants=["JA-00001", "JA-00002", "JA-00003"]
)
```

### Parameters

- `interview_round` (required) - Interview Round name
- `interview_date` (required) - Interview date (YYYY-MM-DD)
- `start_time` (optional) - Start time (HH:MM:SS)
- `end_time` (optional) - End time (HH:MM:SS)
- `time_slot` (optional) - Time slot string (e.g., "09:00:00-10:00:00")
- `job_applicants` (required) - List of Job Applicant names
- `demand` (optional) - Filter by Demand
- `job_opening` (optional) - Filter by Job Opening

### Features

- Prevents duplicate Interview Round per Job Applicant
- Validates Job Applicant stage allows interview
- Returns detailed success/failure report

## Setup

### 1. Add Custom Fields

```python
from recruitment_system.recruitment_system.interview.custom_fields import add_custom_fields_to_interview

result = add_custom_fields_to_interview()
print(result)
```

### 2. Clear Cache and Restart

```bash
bench --site your_site_name clear-cache
bench restart
```

## Interview Round Usage

Use Interview Round to define interview types:
- **Internal HR** - Internal HR screening
- **Internal Technical** - Technical interview
- **Company Interview** - Company/Company interview

Interview Type comes from Interview Round - DO NOT add Interview Type field elsewhere.

## Integration with Application

- Interview is always linked to Job Applicant (HRMS standard)
- Application is auto-linked from Job Applicant
- Interview results automatically update Application stage
- Interview list visible inside Application form

## Files Structure

```
recruitment_system/interview/
├── __init__.py
├── custom_fields.py    # Custom field definitions
├── interview.py        # Interview class extension
├── bulk.py             # Bulk interview creation utility
└── README.md           # This file
```

## Design Principles

1. ✅ Interview Type = Interview Round (HRMS built-in)
2. ✅ Interview always linked to Job Applicant (Application doctype was removed)
3. ✅ Job Applicant controls pipeline and stage
4. ✅ Interview only records execution + result
5. ✅ No duplicate fields, no parallel logic
6. ✅ HRMS functionality remains intact
