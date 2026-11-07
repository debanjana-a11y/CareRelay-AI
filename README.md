## CareRelay-AI

CareRelay turns clinical shift handovers into a collaborative, AI-assisted workflow inside Switch Rooms. Connected to Slack/Discord via Switch, the CareRelay agent monitors a shared ward workspace containing synthetic patient logs, vitals, and pending tasks. At shift change, it generates a structured SBAR briefing directly in the team room, answers incoming clinicians' follow-up questions using shared room context, and updates a live handover checklist as nurses and doctors claim and complete critical tasks together.

## Project Objectives
- Turn Shift Channels into Shared Switch Rooms: Give outgoing staff, incoming staff, and AI agents one shared conversation and workspace context so zero patient details get lost between shifts.
- Enable Interactive Clinical Q&A & Task Tracking: Allow incoming colleagues to query patient logs, clarify anomalies, and update a live markdown handover checklist directly inside chat.
- Enforce Safety & Guardrails: Configure strict agent instructions and Switch guardrails so the agent flags abnormal vitals without inventing medical advice and keeps room context isolated to authorized ward channels.

## How to use app
1. Login to E2B and create an API Key. Export the AI Key in terminal

export E2B_API_KEY="e2b_XXXXX" 

2. python3.11 app.py

3. 