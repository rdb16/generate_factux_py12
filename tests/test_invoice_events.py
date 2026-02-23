"""
Test de récupération et vérification des événements d'une facture sur SuperPDP.

Usage: uv run python tests/test_invoice_events.py <invoice_id>
Exemple: uv run python tests/test_invoice_events.py 16280
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.super_pdp import get_cached_pdp_token

API_BASE = "https://api.superpdp.tech/v1.beta"


def get_invoice_events(invoice_id: int) -> dict:
    """Récupère les infos et événements d'une facture via l'API SuperPDP."""
    token_data = get_cached_pdp_token()
    access_token = token_data["access_token"]

    result = subprocess.run(
        [
            "curl", "-s",
            "-H", f"Authorization: Bearer {access_token}",
            f"{API_BASE}/invoices/{invoice_id}",
        ],
        capture_output=True, text=True, timeout=15,
    )

    data = json.loads(result.stdout)

    if data.get("http_status_code", 200) != 200:
        raise RuntimeError(f"HTTP {data.get('http_status_code')} — {result.stdout}")

    return data


def check_validation(events: list[dict]) -> bool:
    """Vérifie si la facture a été validée (status_code 'api:validated')."""
    return any(e.get("status_code") == "api:validated" for e in events)


def test_invoice_events(invoice_id: int):
    """Récupère un token, appelle l'API et vérifie la validation."""

    print("=" * 60)
    print(f"TEST ÉVÉNEMENTS FACTURE #{invoice_id}")
    print("=" * 60)

    # 1. Token
    print("\n[1/3] Récupération du token...")
    try:
        token_data = get_cached_pdp_token()
    except Exception as e:
        print(f"ERREUR token: {e}")
        return

    token_short = token_data["access_token"][-6:]
    print(f"OK — Token Bearer ...{token_short}")

    # 2. Appel API
    print(f"\n[2/3] Appel GET {API_BASE}/invoices/{invoice_id}...")
    try:
        data = get_invoice_events(invoice_id)
    except RuntimeError as e:
        print(f"ERREUR API: {e}")
        return

    invoice_number = data.get("en_invoice", {}).get("number", "N/A")
    events = data.get("events", [])

    print(f"OK — Facture : {invoice_number}")
    print(f"     Direction : {data.get('direction', 'N/A')}")
    print(f"     Événements : {len(events)}")

    # 3. Vérification validation
    print("\n[3/3] Vérification de la validation...")
    for evt in events:
        status = evt.get("status_code", "")
        text = evt.get("status_text", "")
        created = evt.get("created_at", "")
        print(f"  - [{created}] {status} — {text}")

    # Résultat
    print("\n" + "=" * 60)
    print("RÉSULTAT")
    print("=" * 60)

    if check_validation(events):
        print(f"VALIDÉE — La facture {invoice_number} a été validée par la PDP.")
    else:
        statuses = [e.get("status_code") for e in events]
        print(f"NON VALIDÉE — Statuts trouvés : {statuses}")

    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage : {sys.argv[0]} <invoice_id>")
        print(f"Exemple : uv run python {sys.argv[0]} 16280")
        sys.exit(1)

    try:
        inv_id = int(sys.argv[1])
    except ValueError:
        print(f"ERREUR : '{sys.argv[1]}' n'est pas un ID valide (entier attendu)")
        sys.exit(1)

    test_invoice_events(inv_id)
