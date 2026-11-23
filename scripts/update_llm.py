"""
Push the current prompts/agent_system.md to Retell, replacing the old prompt.
Run after any edit to the prompt file:
    python scripts/update_llm.py
"""
import os
import httpx
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

RETELL_KEY = os.environ["RETELL_API_KEY"]
LLM_ID = os.environ["RETELL_LLM_ID"]
SYSTEM_PROMPT = Path("prompts/agent_system.md").read_text(encoding="utf-8")

print(f"Updating Retell LLM {LLM_ID}...")
print(f"  prompt size: {len(SYSTEM_PROMPT):,} chars")

r = httpx.patch(
    f"https://api.retellai.com/update-retell-llm/{LLM_ID}",
    headers={"Authorization": f"Bearer {RETELL_KEY}"},
    json={
        "general_prompt": SYSTEM_PROMPT,
        "begin_message": "{{opening_line}}",
        "general_tools": [
            {
                "type": "end_call",
                "name": "end_call",
                "description": "End the call politely. Call this when a hard-stop trigger fires or customer declines twice.",
            }
        ],
    },
    timeout=30,
)

if r.status_code not in (200, 201):
    print(f"\nFAIL: status {r.status_code}")
    print(r.text)
    raise SystemExit(1)

print(f"\nOK -- LLM updated.")
print("Every new call from now on uses the new prompt.")