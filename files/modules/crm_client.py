"""
crm_client.py
Real HubSpot CRM integration: contact upsert, persona segmentation, campaign logging.
Uses HubSpot's v3 REST API. Works with a free developer account.
"""

import json
import requests
from datetime import datetime, timezone
from pathlib import Path

HUBSPOT_BASE = "https://api.hubapi.com"
LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
CAMPAIGN_LOG = LOG_DIR / "campaign_log.json"

# ── Helpers ───────────────────────────────────────────────────────────────────

def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _load_log() -> list[dict]:
    if CAMPAIGN_LOG.exists():
        try:
            return json.loads(CAMPAIGN_LOG.read_text())
        except json.JSONDecodeError:
            return []
    return []


def _save_log(entries: list[dict]) -> None:
    CAMPAIGN_LOG.write_text(json.dumps(entries, ensure_ascii=False, indent=2))


# ── Mock contacts (for demo / no real HubSpot account) ───────────────────────

MOCK_CONTACTS = [
    {"email": "yuki.tanaka@example.com",  "firstname": "Yuki",    "lastname": "Tanaka",   "persona": "VIP"},
    {"email": "sofia.lindqvist@example.com","firstname": "Sofia", "lastname": "Lindqvist","persona": "VIP"},
    {"email": "marco.russo@example.com",  "firstname": "Marco",   "lastname": "Russo",    "persona": "REGULAR"},
    {"email": "anna.kowalski@example.com","firstname": "Anna",    "lastname": "Kowalski", "persona": "REGULAR"},
    {"email": "james.chen@example.com",   "firstname": "James",   "lastname": "Chen",     "persona": "AT_RISK"},
    {"email": "nina.patel@example.com",   "firstname": "Nina",    "lastname": "Patel",    "persona": "AT_RISK"},
]


# ── Contact management ────────────────────────────────────────────────────────

def upsert_contacts(token: str, contacts: list[dict] | None = None) -> dict:
    """
    Create or update contacts in HubSpot, tagging each with their persona.
    Uses the batch upsert endpoint (POST /crm/v3/objects/contacts/batch/upsert).
    Falls back to MOCK_CONTACTS when contacts=None.

    Returns a result dict: {"success": int, "errors": list[str]}
    """
    contacts = contacts or MOCK_CONTACTS
    url = f"{HUBSPOT_BASE}/crm/v3/objects/contacts/batch/upsert"

    inputs = [
        {
            "idProperty": "email",
            "id": c["email"],
            "properties": {
                "email":     c["email"],
                "firstname": c.get("firstname", ""),
                "lastname":  c.get("lastname", ""),
                "hs_lead_status": c.get("persona", "REGULAR"),   # custom property reuse
                "acne_persona": c.get("persona", "REGULAR"),     # your custom property
            },
        }
        for c in contacts
    ]

    try:
        resp = requests.post(
            url,
            headers=_headers(token),
            json={"inputs": inputs},
            timeout=10,
        )
        if resp.status_code in (200, 201, 207):
            data = resp.json()
            errors = [r.get("message", "") for r in data.get("errors", [])]
            return {"success": len(inputs) - len(errors), "errors": errors, "raw": data}
        else:
            return {"success": 0, "errors": [f"HTTP {resp.status_code}: {resp.text[:300]}"]}
    except requests.RequestException as e:
        return {"success": 0, "errors": [str(e)]}


def get_contacts_by_persona(token: str, persona: str) -> list[dict]:
    """
    Search HubSpot for contacts matching a given persona tag.
    Returns a list of contact property dicts.
    """
    url = f"{HUBSPOT_BASE}/crm/v3/objects/contacts/search"
    body = {
        "filterGroups": [{
            "filters": [{
                "propertyName": "acne_persona",
                "operator": "EQ",
                "value": persona,
            }]
        }],
        "properties": ["email", "firstname", "lastname", "acne_persona"],
        "limit": 100,
    }
    try:
        resp = requests.post(url, headers=_headers(token), json=body, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("results", [])
        return []
    except requests.RequestException:
        return []


# ── Campaign logging ──────────────────────────────────────────────────────────

def log_campaign(
    token: str,
    product: str,
    newsletters: dict[str, str],
    ab_results: dict,
) -> dict:
    """
    Log a campaign record locally (always) and attempt to create a HubSpot Note
    (a simple activity log) on the first VIP contact as a proof-of-concept.

    Returns the locally stored campaign record dict.
    """
    record = {
        "campaign_id": f"ACN-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}",
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "product": product,
        "personas_sent": list(newsletters.keys()),
        "ab_variant_a_ctr": ab_results.get("A", 0),
        "ab_variant_b_ctr": ab_results.get("B", 0),
        "ab_p_value": ab_results.get("p", 1.0),
        "hubspot_synced": False,
    }

    # Attempt real HubSpot note creation (fire-and-forget)
    if token:
        note_body = (
            f"Campaign sent: {product}\n"
            f"Segments: {', '.join(newsletters.keys())}\n"
            f"A/B CTR — A: {ab_results.get('A', 0):.1%} | B: {ab_results.get('B', 0):.1%}\n"
            f"p-value: {ab_results.get('p', 1):.4f}"
        )
        note_url = f"{HUBSPOT_BASE}/crm/v3/objects/notes"
        note_payload = {
            "properties": {
                "hs_note_body": note_body,
                "hs_timestamp": str(int(datetime.now(timezone.utc).timestamp() * 1000)),
            }
        }
        try:
            r = requests.post(note_url, headers=_headers(token), json=note_payload, timeout=8)
            record["hubspot_synced"] = r.status_code in (200, 201)
            record["hubspot_note_id"] = r.json().get("id") if record["hubspot_synced"] else None
        except requests.RequestException:
            pass

    # Persist locally
    entries = _load_log()
    entries.append(record)
    _save_log(entries)
    return record


def load_campaign_history() -> list[dict]:
    """Return all locally-logged campaign records, newest first."""
    return list(reversed(_load_log()))


# ── Simulated send (newsletter dispatch) ─────────────────────────────────────

def simulate_send(token: str, newsletters: dict[str, str], product: str) -> dict[str, int]:
    """
    Simulate sending newsletters to each persona segment.
    In a real integration this would call the HubSpot Marketing Email API
    or a transactional provider (SendGrid, etc.).

    Returns {persona: recipient_count} based on HubSpot contact search
    (falls back to mock counts if HubSpot search returns nothing).
    """
    MOCK_COUNTS = {"VIP": 2, "REGULAR": 2, "AT_RISK": 2}
    counts: dict[str, int] = {}
    for persona in newsletters:
        if token:
            results = get_contacts_by_persona(token, persona)
            counts[persona] = len(results) if results else MOCK_COUNTS.get(persona, 0)
        else:
            counts[persona] = MOCK_COUNTS.get(persona, 0)
    return counts
