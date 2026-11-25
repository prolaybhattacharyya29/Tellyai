"""
scripts/sync_retell_calls.py

Sync calls directly from Retell AI into Supabase.
Useful when webhook is missed because ngrok/local server was offline.

Usage:
    uv run python scripts/sync_retell_calls.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.sync_service import sync_recent_calls

if __name__ == "__main__":
    result = sync_recent_calls(limit=25)
    print("Sync result:", result)
