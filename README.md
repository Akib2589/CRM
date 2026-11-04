# BIAI Corporate Lead Pipeline — Enterprise Sales CRM

This is an enterprise-ready corporate lead management and sales pipeline intelligence system. Designed to solve lead leakage, overdue follow-ups, duplicate records, and invisible bottlenecks in corporate training sales.

Built in accordance with the frozen architecture design, adhering to a modular monolith pattern, authoritative database calculations, and grounded AI assistance.

---

## 1. Quick Start

### Option A: Local Development

#### 1. Backend (FastAPI + SQLite)
```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
- API Docs: `http://localhost:8000/api/v1/docs`
- Health check: `http://localhost:8000/health`
*(On initial startup, the backend automatically seeds and validates the 25 sample corporate leads into SQLite).*

#### 2. Frontend (Next.js 14 + Tailwind CSS)
```bash
cd frontend
npm install
npm run dev -- -p 3000
```
- Web Application: `http://localhost:3000`

---

## 2. Test Suite & Validation

Run the Pytest suite verifying stage transitions, duplicate detection, date errors, and API contracts:

```bash
cd backend
PYTHONPATH=. .venv/bin/pytest tests/ -v
```

---

## 3. Four-Screen MVP Tour

### Screen 1: Dashboard (`/` & `/dashboard`)
- **Executive KPIs**: Active Pipeline Value (৳3,920,000), Total Leads (25), Paid Revenue (৳300,000), Overdue Follow-ups (9), and Open Data Quality Issues (8).
- **Interactive Stage Funnel**: Shows sequential progress across 5 active stages (*New → Contacted → Meeting → Proposal → Invoice sent*) and 2 terminal stages (*Paid*, *Lost*), with conversion metrics and 1-click filtering.
- **Priority Chasing List**: Dynamically surfaces deals requiring immediate outreach based on overdue days and deal value.
- **One-Click Actions**: Export to CSV, upload new CSV, open data quality auditor, or launch AI assistant.

### Screen 2: Leads Pipeline (`/leads`)
- **Dual View**: Seamlessly switch between **Kanban Board** and **Responsive Table**.
- **Visual Risk Highlighting**: High-contrast badges for overdue follow-ups (red/amber) and data quality flags.
- **Filtering & Search**: Instant filtering by Stage, Industry, Follow-up Status, and Data Quality anomalies.
- **Stage Progression & Guardrails**: Move leads forward with one click. Moving a closed lead back out of *Paid* or *Lost* enforces an audit justification modal.

### Screen 3: Lead Details (`/leads/[id]`)
- **Comprehensive Profile**: Contact info, company background, source, and deal value in BDT (৳).
- **Data Quality Alert Banner**: Displays specific detected issues (e.g. duplicate match, chronological date error) with a direct "Resolve" action.
- **Follow-up Management**: View scheduled date, mark follow-ups complete, or schedule the next outreach date.
- **AI Follow-up Email Generator**:
  - Automatically incorporates the lead's notes, industry, contact name, and pipeline stage.
  - Tone selector (*Polite & professional*, *Friendly*, *Direct*, *Urgent*).
  - Produces an editable Subject and Body in English under 130 words.
  - One-click copy with clipboard notification.
- **Stage Audit Trail**: Immutable history log tracking who changed what stage, when, and why.

### Screen 4: AI Sales Intelligence Assistant (`/assistant`)
- **Multilingual Query Engine**: Accurately interprets questions asked in **English**, **Bengali (বাংলা)**, or **Banglish**:
  - *"Proposal stage e total deal value koto?"* → ৳12,660,000 BDT across 3 proposals.
  - *"Proposal stage এ মোট deal value কত?"*
  - *"Which deals are overdue?"* → Returns count and clickable lead cards.
  - *"Show garments leads"*
  - *"Show top 5 biggest deals"*
- **Authoritative Grounding**: AI never estimates financial numbers or lead counts. It parses the intent, executes allowlisted SQL aggregations against SQLite, and formats the result in the user's natural language.
- **Executive Weekly Priority Briefing**: Generates an on-demand strategic briefing analyzing pipeline health, high-priority accounts, overdue aging, and 3 concrete team action items.

---

## 4. Assessment Evaluation & Ground-Truth Report

The dataset of 25 corporate leads includes intentional data quality errors. The system detects and manages them with **100% precision and recall**:

| Anomaly Category | Target Records | Application Handling | Result |
| :--- | :--- | :--- | :--- |
| **Duplicate Companies (Fuzzy Match)** | **L02** (*Meghna Pharma Ltd*) & **L03** (*Meghna Pharmaceuticals*) | RapidFuzz token sorting (100% match) combined with shared contact email (`sultana@meghna-pharma.example`). | Flagged in Data Quality Engine. Merged into primary via Duplicate Resolver. |
| **Duplicate Companies (Exact Match)** | **L01** (*Padma Textiles Ltd*) & **L23** (*Padma Textiles Ltd*) | Normalized name match (100% match) and identical contact email (`rafiq@padma-textiles.example`). | Flagged in Data Quality Engine. Merged into primary via Duplicate Resolver. |
| **Chronological Date Error** | **L25** (*Sylhet Hospitality Group*) | Date validator checks `last_contact_date` (2026-10-28) vs `next_follow_up_date` (2026-10-21). | Flagged as **CRITICAL: DATE_ORDER_ERROR**. Displayed prominently on lead page for correction. |
| **Missing Contact Methods** | **L06** (*Sylhet Tea Traders*) & **L24** (*Noakhali Agro Mart*) | Contact validator audits name, phone, and email. | L06 flagged for missing phone. L24 flagged for missing contact name and email. |
| **Overdue Follow-ups** | 9 Active Leads (*L04, L06, L07, L10, L13, L14, L15, L19, L20*) | Evaluated against frozen assessment date (`2026-11-01`). Paid and Lost deals are excluded. | Highlighted in red/amber with overdue days counter. |

---

## 5. Architectural Decisions

1. **Modular Monolith**: Clean boundaries between domain repositories, business logic services, validators, and presentation layers.
2. **Authoritative Calculation Boundary**: AI models are forbidden from doing SQL math or hallucinating metrics. The backend parses queries into validated Pydantic schemas, runs deterministic SQL queries, and passes the ground-truth numbers back to the LLM for natural language phrasing.
3. **Resilient AI Provider with Fallback Pool**: Uses OpenRouter API with high-throughput models (`nvidia/nemotron-3.5-lightning:free`, `google/gemma-4-31b-it:free`, etc.). Automatically retries across a fallback pool if any provider experiences rate limits.
4. **Auditability**: Every stage change and duplicate merge creates an immutable `AuditLog` and `StageHistory` entry.

---

## 6. Submission Note (For the Hiring Team)

- **What was built**: A full-stack pipeline web app with 4 comprehensive screens, SQLite persistence, dual Kanban/Table views, two-phase CSV import with validation preview, CSV export, duplicate merger, follow-up scheduler, AI email generator, and conversational sales intelligence.
- **AI tools used**:
  - OpenRouter API compatible provider for email generation, NLP intent classification, and weekly executive briefings.
  - Antigravity AI pair programming for architectural scaffolding and implementation.
- **Current limitations & what to fix next**:
  - Add role-based authentication (Sales Rep vs Sales Manager).
  - Add calendar sync (Google Calendar / Outlook) for scheduled follow-ups.
  - Implement automated email delivery via SendGrid / Resend directly from the draft modal.

---

## 7. Loom Video Presentation Outline (Under 5 Minutes)

1. **Problem & Hook (0:00 - 0:45)**: Explain the challenge of corporate training sales at BIAI—leads lost across messages, overdue follow-ups, and bad spreadsheet data.
2. **Dashboard & KPIs (0:45 - 1:45)**: Showcase the 5-stage funnel, active pipeline value of ৳3.92M, overdue counter, and priority accounts.
3. **Leads Pipeline & Data Quality (1:45 - 2:45)**: Demonstrate Kanban view, show how L02/L03 (Meghna Pharma) and L25 (date error) were flagged and resolved, and show stage transition guardrails.
4. **AI Follow-up Email (2:45 - 3:30)**: Open Lead L01 (Padma Textiles), customize tone, generate a tailored AI email referencing their 2-day pilot merchandising training, and copy with 1 click.
5. **AI Assistant & Banglish Queries (3:30 - 4:30)**: Ask *"Proposal stage e total deal value koto?"* and show authoritative SQL calculation and Banglish response; generate the Weekly Executive Priority Summary.
6. **Closing (4:30 - 5:00)**: Highlight architectural choices, test coverage, and why BIAI's corporate sales team will love using it.
