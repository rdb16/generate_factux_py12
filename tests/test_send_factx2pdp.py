"""Test d'envoi de facture Factur-X vers la PDP SuperPDP."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.super_pdp import get_cached_pdp_token

token_response = get_cached_pdp_token()
access_token = token_response["access_token"]
print(f"Token obtenu : {access_token[:20]}...")
print(f"Expire dans : {token_response.get('expires_in')} secondes")
