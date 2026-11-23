"""
Create a Retell Agent tied to the LLM config created in Part C.
Returns an agent_id that we save in .env.
Run once: python scripts/create_agent.py
"""
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

RETELL_KEY = os.environ["RETELL_API_KEY"]
LLM_ID = os.environ["RETELL_LLM_ID"]
VOICE_ID = os.environ["VIETNAMESE_VOICE_ID"]
NGROK_DOMAIN = os.environ["NGROK_DOMAIN"]

webhook_url = f"https://{NGROK_DOMAIN}/retell-webhook"

agent_config = {
    "agent_name": "FE Credit Demo Agent (English testing)",
    "voice_id": VOICE_ID,
    "voice_speed": 1.0,
    "language": "en-US",
    "response_engine": {
        "type": "retell-llm",
        "llm_id": LLM_ID,
    },
    "webhook_url": webhook_url,
    "end_call_after_silence_ms": 15000,
    "max_call_duration_ms": 240000,
    "interruption_sensitivity": 1,
}

print("Creating Retell Agent...")
print(f"  voice_id:    {VOICE_ID}")
print(f"  language:    en-US")
print(f"  llm_id:      {LLM_ID}")
print(f"  webhook_url: {webhook_url}")

r = httpx.post(
    "https://api.retellai.com/create-agent",
    headers={"Authorization": f"Bearer {RETELL_KEY}"},
    json=agent_config,
    timeout=20,
)

if r.status_code not in (200, 201):
    print(f"\nFAIL: status {r.status_code}")
    print(r.text)
    raise SystemExit(1)

data = r.json()
agent_id = data["agent_id"]
print(f"\nOK -- agent_id = {agent_id}")
print("\nNow paste this into your .env file:")
print(f"RETELL_AGENT_ID={agent_id}")