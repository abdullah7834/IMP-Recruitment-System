# Overseas Recruitment ATS – Master Build Plan
## Tech Stack: Frappe ERP + Frappe HR + Frappe Drive

---

## BUILD PHILOSOPHY

We will build the system in **three strict phases**:

1. **Strong Foundation** (Data correctness, structure, compliance)
2. **Automation Layer** (Reduce manual work)
3. **Intelligence Layer** (Recommendations, insights)

⚠️ No automation or intelligence will be added before the foundation is complete.

---

# PHASE 1 — STRONG FOUNDATION (CORE SYSTEM)

### Goal
Build a **rock-solid overseas recruitment tracking system** that:
- Matches real-life recruitment workflows
- Prevents data duplication
- Enforces compliance rules
- Is scalable and future-proof

---

## MODULE 1: APPLICANT MASTER (FOUNDATION CORE)

### Purpose
Create a **single, permanent record** for each candidate.

### Key Principles
- CNIC = Unique Identifier
- One applicant can apply to multiple jobs
- Applicant owns documents, not jobs

### Custom DocTypes
- Applicant
- Applicant Skill (Child)
- Applicant Experience (Child)
- Applicant Education (Child)
- Applicant Document (Child)

### What This Module Must Handle
- Manual entry (office use)
- WhatsApp / CV uploads
- Duplicate prevention using CNIC
- Complete applicant profile storage

### Drive Structure (Auto-Created)
/Applicants/{CNIC}/
/CV/
/Passport/
/Certificates/
/Licenses/
/Medical/
/Police/





---

## MODULE 2: COMPANY & LEGAL SETUP

### Purpose
Manage foreign employers and their legal authorization.

### Use Existing DocTypes
- Company (ERPNext)

### Customizations to Company
- Company Type (Foreign Employer)
- Recruitment Active (Yes/No)
- Official Recruitment Emails
- Country
- Linked Hiring Rules

### Custom DocTypes
- Employer Hiring Rules

### Drive Structure
/Companies/{Company Name}/
/Legal/
/Demands/
/Job_Openings/
/Batches/



---

## MODULE 3: DEMAND MANAGEMENT

### Purpose
Represent **Demand Letters** formally in the system.

### Custom DocTypes
- Demand

### Demand Lifecycle
- Received
- Sent to Bureau
- Approved
- Closed

### Demand Contains
- Company
- Job Title
- Quantity
- Salary & Benefits
- Demand Letter (Drive link)
- POA (Drive link)

### Automation  
- Demand → Job Opening creation

---

## MODULE 4: JOB OPENING (CUSTOMIZED HR)

### Purpose
Convert demands into actionable jobs.

### Customize Existing DocType
- Job Opening (Frappe HR)

### Custom Fields to Add
- Linked Demand
- Age Min / Max
- Required Documents
- Experience Required
- Internal Interview Required
- Trade Test Required

### Output
- Published job (website)
- Active ATS pipeline

---

## MODULE 5: APPLICATION (ATS TRACKER CORE)

### Purpose
Track **Applicant ↔ Job** lifecycle.

### Custom DocTypes
- Application

### Why Custom?
- Frappe Job Applicant is job-centric
- Overseas recruitment needs applicant-centric tracking

### Application Tracks
- Current Stage
- Internal HR result
- Technical result
- Company result
- Visa status
- Final outcome

### Pipeline Stages
- Applied
- Screening
- Documents Pending
- Internally Selected
- Internal Rejected
- Batched
- Company Selected
- Company Rejected   
- Visa Processing
- Deployed

---

## MODULE 6: INTERVIEWS

### Purpose
Handle internal and Company interviews.

### Use Existing DocType
- Interview (Frappe HR)

### Custom Fields
- Interview Type (HR / Technical / Company) 
- Interview Level (Internal / Company)
- Result (Pass / Fail / Hold)

---

## MODULE 7: BATCH MANAGEMENT (OVERSEAS SPECIFIC)

### Purpose
Group **internally selected candidates** before Company interview.

### Custom DocTypes
- Batch
- Batch Candidate (Child)

### Batch Rules
- Batch is created **after internal selection**
- Batch is sent to Company for review/interview

### Drive Structure
/Companies/{Company}/Batches/{Batch Name}/
Shortlisted_Candidates.xlsx



---

## MODULE 8: SYSTEM CHECKS & COMPLIANCE (FOUNDATION)

### Purpose
Prevent invalid candidates from moving forward.

### Mandatory Checks
- CNIC uniqueness
- Passport expiry ≥ 6 months
- Age within job limits
- Required documents uploaded
- Medical Passed before Visa
- Deployed candidates excluded

### Enforcement
- Workflow conditions
- Validation hooks
- Server scripts

---

# PHASE 2 — AUTOMATION (AFTER FOUNDATION)

### Goal
Reduce manual work by 60–80%.

### Planned Automation Modules
- CV Parsing (PDF / DOC)
- OCR for Passport & CNIC
- Auto folder creation
- Auto email logging
- Auto batch document generation

⚠️ Only after Phase 1 is stable.

---

# PHASE 3 — INTELLIGENCE (ADVANCED)

### Goal
Help recruiters **decide faster**, not replace them.

### Intelligence Features
- Job → Candidate matching
- Candidate → Job recommendations
- Readiness scoring
- Bottleneck dashboards
- Predictive delays

---

## BUILD ORDER (STRICT)

1. Applicant Master
2. Company & Hiring Rules
3. Demand
4. Job Opening customization
5. Application tracker
6. Interviews
7. Batch
8. Compliance checks

---

## ESTIMATED TIMELINE

- Phase 1 (Foundation): 6–8 weeks
- Phase 2 (Automation): 4–6 weeks
- Phase 3 (Intelligence): 6–8 weeks

---

## NON-NEGOTIABLE PRINCIPLES

- Applicant ≠ Job
- CNIC is permanent identity
- No duplicate CV uploads
- Drive stores files, ATS stores logic
- System blocks invalid actions
- Human makes final decisions

---

## NEXT STEP

Start implementation with:
👉 **Module 1: Applicant Master**
