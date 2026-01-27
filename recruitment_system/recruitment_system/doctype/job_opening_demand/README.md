# Job Opening Demand Integration

This module customizes the Frappe HR "Job Opening" doctype to integrate with the custom "Demand" doctype.

## Files Created

1. **`job_opening_demand.py`** - Server-side methods
   - `get_demand_positions()` - Fetch all positions from a Demand
   - `get_demand_position_details()` - Get specific position details
   - `get_demand_age_requirements()` - Get age requirements from Demand

2. **`job_opening_demand.js`** - Client-side script
   - Handles `linked_demand` field change
   - Handles `demand_position` field change
   - Auto-fills Job Opening fields

3. **`add_custom_fields.py`** - Script to add custom fields

## Setup Instructions

### Step 1: Add Custom Fields

Run this command to add custom fields to Job Opening:

```bash
bench --site [your-site-name] console
```

Then execute:
```python
from recruitment_system.recruitment_system.doctype.job_opening_demand.add_custom_fields import add_custom_fields_to_job_opening
add_custom_fields_to_job_opening()
```

Or via one-line command:
```bash
bench --site [your-site-name] execute recruitment_system.recruitment_system.doctype.job_opening_demand.add_custom_fields.add_custom_fields_to_job_opening
```

### Step 2: Clear Cache

```bash
bench --site [your-site-name] clear-cache
bench --site [your-site-name] clear-website-cache
```

### Step 3: Test

1. Create a Demand with positions
2. Create a Job Opening
3. Select a Demand in "Linked Demand" field
4. Verify "Demand Position" dropdown is populated
5. Select a position and verify fields are auto-filled

## Custom Fields Added

- `linked_demand` (Link → Demand) [Mandatory]
- `demand_position` (Select) [Mandatory]
- `experience_required` (Small Text)
- `education_required` (Small Text)
- `age_min` (Int)
- `age_max` (Int)
- `internal_hr_required` (Check)
- `technical_interview_required` (Check)
- `trade_test_required` (Check)

## Functionality

- **When `linked_demand` is selected:** Fetches positions and populates `demand_position` dropdown
- **When `demand_position` is selected:** Auto-fills Job Opening fields from position data
- **Fields remain editable** after autofill (snapshot behavior)
