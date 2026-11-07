import os
from e2b import Sandbox
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
from langchain.tools import tool
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from slack_sdk import WebClient
from dotenv import load_dotenv

load_dotenv()

slack_client = WebClient(token=os.environ["SLACK_USER_TOKEN"])
channel = os.environ["CHANNEL_ID"]

print("1. Creating E2B sandbox (10 min timeout)...")
e2b_sandbox = Sandbox.create(timeout=600)

try:
    print("2. Installing pandas & matplotlib in sandbox...")
    e2b_sandbox.commands.run("pip install -q pandas matplotlib")

    with open("data/ward_a_vitals.csv", "rb") as f:
        vitals_bytes = f.read()

    with open("data/shift_notes.txt", "rb") as f:
        notes_bytes = f.read()

    e2b_sandbox.files.make_dir("data")
    e2b_sandbox.files.write("data/ward_a_vitals.csv", vitals_bytes)
    e2b_sandbox.files.write("data/shift_notes.txt", notes_bytes)
    print("3. Uploaded ward_a_vitals.csv and shift_notes.txt to E2B sandbox!")

    @tool(parse_docstring=True)
    def inspect_ward_data_and_plot() -> str:
        """Analyze patient vitals CSV and shift notes in the sandbox, detect abnormal vitals, and generate vitals_alert.png."""
        analysis_script = """
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("data/ward_a_vitals.csv")
with open("data/shift_notes.txt", "r", encoding="utf-8") as f:
    notes = f.read()

df["Short_Time"] = df["Timestamp"].astype(str).str.split().str[-1]
df["Label"] = df["Bed_ID"] + " (" + df["Patient_Name"] + ")"

# Dynamic threshold detection
alerts = df[(df["Temp_C"] > 38.0) | (df["Heart_Rate_bpm"] > 100) | (df["SpO2_Pct"] < 92)]

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
for label, grp in df.groupby("Label"):
    ax1.plot(grp["Short_Time"], grp["Temp_C"], marker="o", linewidth=2, label=label)
    ax2.plot(grp["Short_Time"], grp["SpO2_Pct"], marker="s", linewidth=2, label=label)

ax1.axhline(38.0, color="red", linestyle="--", linewidth=1.2, label="Fever Alert (38.0°C)")
ax1.set_ylabel("Temperature (°C)")
ax1.set_title("Shift Handover — Patient Vitals Trend")
ax1.grid(True, alpha=0.3)
ax1.legend(loc="upper left", fontsize=8)

ax2.axhline(92.0, color="red", linestyle="--", linewidth=1.2, label="Low SpO2 Alert (92%)")
ax2.set_ylabel("SpO2 (%)")
ax2.set_xlabel("Time")
ax2.grid(True, alpha=0.3)
ax2.legend(loc="lower left", fontsize=8)

plt.tight_layout()
plt.savefig("vitals_alert.png", dpi=150)

print("=== ABNORMAL VITALS DETECTED ===")
print(alerts.to_string(index=False) if not alerts.empty else "None")
print("\\n=== FULL VITALS TABLE ===")
print(df.drop(columns=["Short_Time", "Label"]).to_string(index=False))
print("\\n=== SHIFT NOTES ===")
print(notes)
"""
        e2b_sandbox.files.write("analyze.py", analysis_script)
        res = e2b_sandbox.commands.run("python3 analyze.py")
        return res.stdout

    @tool(parse_docstring=True)
    def slack_send_message(text: str, file_path: str | None = None) -> str:
        """Send a message to the team Slack channel, optionally attaching an image file from the sandbox.

        Args:
            text: The SBAR handover briefing text to send.
            file_path: Path of the generated chart image in the sandbox (e.g., 'vitals_alert.png').
        """
        if not file_path:
            slack_client.chat_postMessage(channel=channel, text=text)
        else:
            chart_bytes = bytes(e2b_sandbox.files.read(file_path, format="bytes"))
            slack_client.files_upload_v2(
                channel=channel,
                content=chart_bytes,
                filename=os.path.basename(file_path),
                initial_comment=text,
            )

        return "Message and attachment sent to Slack."

    model = ChatOllama(
        model="qwen2.5:7b",
        base_url="http://192.168.211.1:11434",
        num_ctx=4096,
        temperature=0.0,
    )

    agent = create_agent(
        model=model,
        tools=[inspect_ward_data_and_plot, slack_send_message],
        checkpointer=InMemorySaver(),
    )

    config = {"configurable": {"thread_id": "ward-a-handover-1"}}

    prompt_content = """You are CareRelay, a clinical shift handover assistant.

Complete these steps:
1. Call `inspect_ward_data_and_plot` to inspect the patient vitals CSV, shift notes, detected abnormal vitals, and generate `vitals_alert.png`.
2. Call `slack_send_message` with `file_path="vitals_alert.png"` and a concise, scannable SBAR Shift Handover Briefing in `text`:
   - *CRITICAL / HIGH-PRIORITY ALERTS*: Abnormal patients, exact vitals, and urgent pending tasks.
   - *STABLE PATIENTS*: 1-line SBAR summary for remaining patients.
   - *INCOMING SHIFT ACTION CHECKLIST*: `[ ] <Time> - <Bed/Patient>: <Task>` extracted from the shift notes.
   - Invite incoming clinicians to reply in chat to claim tasks.

Rely strictly on the returned data; never invent clinical values."""

    print("4. Running CareRelay agent...")
    for chunk in agent.stream(
        {"messages": [HumanMessage(content=prompt_content)]},
        config=config,
        stream_mode="updates",
    ):
        for node, update in chunk.items():
            if "messages" in update and update["messages"]:
                update["messages"][-1].pretty_print()

finally:
    e2b_sandbox.kill()
    print("5. Sandbox cleaned up.")