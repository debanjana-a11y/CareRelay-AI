# CareRelay — AI Clinical Shift Handover in Switch Rooms

**CareRelay** turns clinical shift handovers into a collaborative team workflow inside **Switch Rooms**. Connected to Slack (`#shift-handover`), CareRelay ingests patient vitals time-series (`data/ward_a_vitals.csv`) and outgoing nurse shift logs (`data/shift_notes.txt`), runs dynamic anomaly detection and matplotlib charting inside an **E2B Sandbox** powered by **Ollama (`qwen2.5:7b`)**, and posts structured **SBAR** (*Situation, Background, Assessment, Recommendation*) alerts with visual vitals charts (`vitals_alert.png`) directly into the team room so incoming clinicians can review critical flags and claim pending tasks together.

## Architecture
- **Switch Room (`#shift-handover`)**: Shared room context and agent instructions (`AGENTS.md`, `handover_checklist.md`) bridging team chat and clinical workspace files.
- **E2B Code Interpreter Sandbox**: Isolated Python execution environment generating multi-panel vitals trend charts (`Temp_C`, `SpO2_Pct`) against clinical safety thresholds (`>38.0°C`, `<92% SpO2`).
- **Ollama (`qwen2.5:7b`) + LangGraph**: Synthesizes structured SBAR briefings strictly grounded in patient records without hallucinating clinical values.
- **Slack Integration**: Delivers visual alert charts and interactive shift checklists directly into the clinical team channel.
