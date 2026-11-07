import os
import io
import pandas as pd
import matplotlib.pyplot as plt
from slack_sdk import WebClient
from dotenv import load_dotenv

load_dotenv()

client = WebClient(token=os.environ["SLACK_USER_TOKEN"])
channel = os.environ["CHANNEL_ID"]

# Generate real vitals_alert.png chart from data/ward_a_vitals.csv in <1 second
df = pd.read_csv("data/ward_a_vitals.csv")
df["Short_Time"] = df["Timestamp"].astype(str).str.split().str[-1]
df["Label"] = df["Bed_ID"] + " (" + df["Patient_Name"] + ")"

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
for label, grp in df.groupby("Label"):
    ax1.plot(grp["Short_Time"], grp["Temp_C"], marker="o", linewidth=2, label=label)
    ax2.plot(grp["Short_Time"], grp["SpO2_Pct"], marker="s", linewidth=2, label=label)

ax1.axhline(38.0, color="red", linestyle="--", linewidth=1.2, label="Fever Alert (38.0°C)")
ax1.set_ylabel("Temperature (°C)")
ax1.set_title("Ward A Shift Handover — Critical Vitals Trends")
ax1.grid(True, alpha=0.3)
ax1.legend(loc="upper left", fontsize=8)

ax2.axhline(92.0, color="red", linestyle="--", linewidth=1.2, label="Low SpO2 Alert (92%)")
ax2.set_ylabel("SpO2 (%)")
ax2.set_xlabel("Time")
ax2.grid(True, alpha=0.3)
ax2.legend(loc="lower left", fontsize=8)

plt.tight_layout()
buf = io.BytesIO()
plt.savefig(buf, format="png", dpi=150)
buf.seek(0)

sbar_briefing = """*WARD A — CLINICAL SHIFT HANDOVER BRIEFING (SBAR)*

*CRITICAL / HIGH-PRIORITY ALERTS*
• *Bed-102 — Rohan Sharma (67M | Pneumonia):* High fever spike to *39.4°C* (up from 37.4°C), tachycardia (*118 bpm*), SpO2 dipped to *91%*, chills noted. *Urgent:* Blood culture draw due at *18:00* before second antibiotic (Dr. Sen notified).
• *Bed-104 — Meera Nair (73F | COPD Exacerbation):* SpO2 dropped from 94% to *88%* on room air at 16:00; placed on 2L/min nasal cannula O2 at 16:10. *Urgent:* Re-check SpO2 and ABG at *18:30* (escalate to ICU if SpO2 < 90% on 2L O2).

*STABLE PATIENTS*
• *Bed-101 — Aarav Patel (54M | Post-Op Appendectomy):* Afebrile (37.0°C), vitals stable (HR 78, SpO2 98%), tolerating clear liquids.
• *Bed-103 — Ananya Das (41F | Acute Gastritis):* Stable (Temp 36.7°C, HR 71, SpO2 99%), no vomiting since 10:00 AM.

*INCOMING SHIFT ACTION CHECKLIST*
- [ ] *18:00* — Bed-102 (Rohan Sharma): URGENT blood culture draw before second antibiotic
- [ ] *18:30* — Bed-104 (Meera Nair): Re-check SpO2 and arterial blood gas (ABG)
- [ ] *19:30* — Bed-103 (Ananya Das): Transition to oral diet at dinner & prepare discharge summary
- [ ] *20:00* — Bed-101 (Aarav Patel): Check surgical dressing; verify afebrile for morning discharge

_Incoming evening team: Reply in this Switch Room to query patient records or claim checklist tasks!_"""

client.files_upload_v2(
    channel=channel,
    content=buf.getvalue(),
    filename="vitals_alert.png",
    initial_comment=sbar_briefing,
)
print("Demo SBAR briefing and vitals_alert.png posted to Slack!")
