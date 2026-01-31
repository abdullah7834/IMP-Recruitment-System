# Job Opening and Job Applicant Logic Explanation

## Overview

This document explains how the Demand → Job Opening → Job Applicant flow works in the recruitment system.

## Architecture Flow

```
Demand (with Positions)
    ↓
Job Opening (linked to Demand + Position)
    ↓
Job Applicant (linked to Job Opening)
```

## 1. Job Opening Logic

### Custom Fields in Job Opening:
- `linked_demand` (Link → Demand) - Links Job Opening to a Demand
- `demand_position` (Select) - Position from the Demand's positions table

### How It Works:

1. **When `linked_demand` is selected:**
   - JavaScript calls `get_demand_positions(demand_name)`
   - Server fetches all positions from Demand's child table (`Demand Positons`)
   - Extracts `job_title` from each position
   - Populates `demand_position` Select dropdown with these job titles

2. **When `demand_position` is selected:**
   - JavaScript calls `get_demand_position_details(demand_name, position_job_title)`
   - Server returns position details (experience, education, salary, etc.)
   - Auto-fills Job Opening fields:
     - `job_title` = position.job_title
     - `experience_required` = position.experience_required
     - `education_required` = position.education_required
     - `planned_vacancies` = position.quantity
     - `lower_range` = position.basic_sallary
   - Also fetches age requirements from Demand level

### Files:
- **Server:** `job_opening_demand/job_opening_demand.py`
  - `get_demand_positions()` - Fetches positions from Demand
  - `get_demand_position_details()` - Gets specific position details
  - `get_demand_age_requirements()` - Gets age min/max from Demand

- **Company:** `public/js/job_opening_demand.js`
  - Handles `linked_demand` change → populates `demand_position` dropdown
  - Handles `demand_position` change → auto-fills Job Opening fields

## 2. Job Applicant Logic

### Custom Fields in Job Applicant:
- `applicant` (Link → Applicant) - Links to Applicant master
- `linked_demand` (Link → Demand) - Links to Demand
- `demand_position` (Select) - Position from Demand
- `job_title` (Link → Job Opening) - **Standard HRMS field** (label: "Job Opening")

### How It Works:

1. **When `linked_demand` is selected:**
   - JavaScript calls `get_demand_positions(demand_name)` (reuses Job Opening method)
   - Populates `demand_position` Select dropdown with position job titles

2. **When `demand_position` is selected:**
   - JavaScript calls `get_job_opening_by_demand_position(demand_name, demand_position)`
   - Server searches for Job Opening where:
     - `linked_demand` = selected demand
     - `demand_position` = selected position
   - If found: Auto-populates `job_title` field (which is the Job Opening Link field)
   - If not found: Shows info message "Job Opening is not found"

### Files:
- **Server:** `job_applicant_custom_fields/add_custom_fields.py`
  - `get_job_opening_by_demand_position()` - Finds Job Opening by demand + position

- **Company:** `public/js/job_applicant.js`
  - Handles `linked_demand` change → populates `demand_position` dropdown
  - Handles `demand_position` change → finds and populates `job_title` (Job Opening)

## Important Field Names

### Job Applicant:
- **Fieldname:** `job_title`
- **Label:** "Job Opening"
- **Type:** Link → Job Opening
- **Note:** This is a **standard HRMS field**, not a custom field!

## Custom Fields Storage

### Where Custom Fields Are Stored:
Custom fields are stored in the **database** in the `Custom Field` doctype. They are:
- Created when you run `add_custom_fields_to_job_opening()` or `add_custom_fields_to_job_applicant()`
- Stored in: `tabCustom Field` table
- Each custom field is a document with:
  - `dt` (DocType) = "Job Opening" or "Job Applicant"
  - `fieldname` = the field name
  - `fieldtype` = Data, Select, Link, etc.
  - Other properties (label, options, etc.)

### Do You Need Fixtures?
- **No, you don't need fixtures** for custom fields to work
- Custom fields are created dynamically via Python scripts
- Fixtures are only needed if you want to:
  - Export/backup custom field definitions
  - Migrate custom fields to another site
  - Version control custom field definitions

### To Export Custom Fields (Optional):
```bash
bench --site [site-name] export-fixtures
```
This creates JSON files in `apps/recruitment_system/recruitment_system/fixtures/` that can be imported to other sites.

## Data Flow Diagram

```
┌─────────────────┐
│     Demand      │
│  - Has Positions│
│    (child table)│
└────────┬────────┘
         │
         │ linked_demand
         ↓
┌─────────────────┐
│   Job Opening   │
│ - linked_demand │
│ - demand_position│
│   (from Demand) │
└────────┬────────┘
         │
         │ job_title (Link)
         ↓
┌─────────────────┐
│  Job Applicant  │
│ - linked_demand │
│ - demand_position│
│ - job_title     │
│   (Job Opening) │
└─────────────────┘
```

## Key Points

1. **Job Opening** is created first with Demand + Position
2. **Job Applicant** then finds the matching Job Opening by Demand + Position
3. The relationship is: Demand → Job Opening → Job Applicant
4. Custom fields are stored in database, not in fixtures (unless exported)
5. Standard HRMS fields (like `job_title` in Job Applicant) are part of the core doctype
