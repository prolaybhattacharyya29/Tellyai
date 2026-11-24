"""
Loads campaigns metadata from data/campaigns.json.
Provides CAMPAIGNS dictionary (keyed by campaign ID) and CAMPAIGNS_LIST.
"""
import json
from pathlib import Path

CAMPAIGNS_JSON_PATH = Path("data/campaigns.json")


def load_campaigns() -> list[dict]:
    path = CAMPAIGNS_JSON_PATH
    if not path.exists():
        alt = Path(__file__).resolve().parent.parent / "data/campaigns.json"
        if alt.exists():
            path = alt
        else:
            return []
    return json.loads(path.read_text(encoding="utf-8"))


CAMPAIGNS_LIST = load_campaigns()
CAMPAIGNS = {c["id"]: c for c in CAMPAIGNS_LIST}
