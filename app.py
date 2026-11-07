import os
import csv
import io
from e2b import Sandbox
from langchain_e2b import E2BSandbox
from deepagents import create_deep_agent
from langchain_ollama import ChatOllama
from langchain_core.utils.uuid import uuid7
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage
from langchain.tools import tool
from slack_sdk import WebClient
from dotenv import load_dotenv

load_dotenv()

slack_token = os.environ["SLACK_USER_TOKEN"]
slack_client = WebClient(token=slack_token)
channel = os.environ["CHANNEL_ID"]

e2b_sandbox = Sandbox.create()
backend = E2BSandbox(sandbox=e2b_sandbox)

@tool(parse_docstring=True)
def slack_send_message(text: str, file_path: str | None = None) -> str:
    """Send a message, optionally including attachments such as images.

    Args:
        text: text content of the message.
        file_path: file path of the attachment in the sandbox filesystem.
    """
    if not file_path:
        slack_client.chat_postMessage(channel=channel, text=text)
    else:
        fp = backend.download_files([file_path])
        slack_client.files_upload_v2(
            channel=channel,
            content=fp[0].content,
            initial_comment=text,
        )
    return "Message sent."

with open("data/ward_a_vitals.csv", "rb") as f:
    vitals_bytes = f.read()

with open("data/shift_notes.txt", "rb") as f:
    notes_bytes = f.read()

backend.upload_files([
    ("data/ward_a_vitals.csv", vitals_bytes),
    ("data/shift_notes.txt", notes_bytes),
])

print("Uploaded ward_a_vitals.csv and shift_notes.txt to E2B sandbox!")

model = ChatOllama(
    model="qwen2.5:7b", 
    base_url="http://192.168.211.1:11434",
    num_ctx=8192,
    temperature=0.0
)

agent = create_deep_agent(
    model=model,
    tools=[slack_send_message],
    backend=backend,
    checkpointer=InMemorySaver()
)

thread_id = str(uuid7())
config = {"configurable": {"thread_id": thread_id}}

prompt_content = """You are a clinical shift handover assistant.

Follow these exact steps:
1. Read `data/ward_a_vitals.csv` and `data/shift_notes.txt` from the current workspace.
2. Write and run a Python script to dynamically inspect all patients in the CSV and flag any abnormal vitals or concerning trends (e.g., Temp > 38.0°C, Heart Rate > 100 bpm, SpO2 < 92%, or rapid changes across timestamps).
3. Generate a clean, high-resolution 2-panel matplotlib chart saved to `vitals_alert.png` plotting all patients across the available timestamps:
   - Top panel: Temperature (°C) trends for every bed/patient, with a horizontal dashed threshold line at 38.0°C.
   - Bottom panel: Oxygen Saturation (SpO2 %) trends for every bed/patient, with a horizontal dashed threshold line at 92%.
4. Write a concise, scannable Shift Handover Briefing in SBAR format based strictly on what you found in the files:
   - **CRITICAL / HIGH-PRIORITY ALERTS:** List any patients with abnormal vitals or urgent flags from the notes, including their latest values and urgent pending tasks.
   - **STABLE PATIENTS:** Provide a brief 1-line SBAR status for the remaining patients.
   - **INCOMING SHIFT ACTION CHECKLIST:** Extract all pending tasks and due times from the shift notes into an interactive checklist (`[ ] <Time> - <Bed/Patient>: <Task>`).
5. Call your messaging tool once to send the SBAR handover briefing along with `vitals_alert.png` to the team chat room.

Rules:
- Rely strictly on the provided CSV and shift notes; do not invent clinical values, dosages, or diagnoses.
- End your message by inviting the incoming clinical team to reply and claim pending tasks from the checklist."""

input_payload = {"messages": [HumanMessage(content=prompt_content)]}

try:
    for event in agent.stream(input_payload, config=config, stream_mode="values"):
        if "messages" in event and event["messages"]:
            latest_msg = event["messages"][-1]
            latest_msg.pretty_print()

finally:
    e2b_sandbox.kill()