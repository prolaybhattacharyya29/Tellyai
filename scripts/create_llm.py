"""
Register the FE Credit agent's system prompt with Retell.
Returns an llm_id we save in .env for reuse.
Run once: python scripts\create_llm.py
"""
import os
import httpx
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

RETELL_KEY = os.environ["RETELL_API_KEY"]
SYSTEM_PROMPT = Path("prompts/agent_system.md").read_text(encoding="utf-8")

llm_config = {
    "general_prompt": SYSTEM_PROMPT,
    "begin_message": "{{opening_line}}",
    "general_tools": [
        {
            "type": "end_call",
            "name": "end_call",
            "description": "End the call politely when the customer declines twice or asks to hang up.",
        }
    ],
    "states": [],
}

print("Creating Retell LLM config...")
r = httpx.post(
    "https://api.retellai.com/create-retell-llm",
    headers={"Authorization": f"Bearer {RETELL_KEY}"},
    json=llm_config,
    timeout=20,
)

if r.status_code != 201 and r.status_code != 200:
    print(f"FAIL: status {r.status_code}")
    print(r.text)
    raise SystemExit(1)

data = r.json()
llm_id = data["llm_id"]
print(f"\nOK — llm_id = {llm_id}")
print("\nNow paste this into your .env file:")
print(f"RETELL_LLM_ID={llm_id}")