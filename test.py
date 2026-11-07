import os
from slack_sdk import WebClient
from dotenv import load_dotenv

load_dotenv()

client = WebClient(token=os.environ["SLACK_USER_TOKEN"])
channel = os.environ["CHANNEL_ID"]

client.files_upload_v2(
    channel=channel,
    content=b"CareRelay test attachment",
    filename="test.txt",
    initial_comment="CareRelay permission test successful!",
)
print("Sent!")