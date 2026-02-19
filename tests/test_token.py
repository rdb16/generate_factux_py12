"""
Script de test pour vérifier l'authentification OAuth2 SuperPDP.

Usage: uv run python tests/test_token.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.super_pdp import get_pdp_token, check_pdp_token


def test_pdp_token():
    """Récupère un token, vérifie sa validité et affiche les infos entreprise."""

    print("=" * 60)
    print("TEST AUTHENTIFICATION SUPERPDP")
    print("=" * 60)

    # 1. Récupérer le token OAuth2
    print("\n[1/2] Récupération du token OAuth2...")
    try:
        token = get_pdp_token()
    except (EnvironmentError, RuntimeError) as e:
        print(f"ERREUR get_pdp_token: {e}")
        return

    print(f"OK - Token obtenu: {token[:20]}...{token[-10:]}")

    # 2. Vérifier le token via /companies/me
    print("\n[2/2] Vérification du token via /companies/me...")
    try:
        company_info = check_pdp_token(token)
    except (ValueError, RuntimeError) as e:
        print(f"ERREUR check_pdp_token: {e}")
        return

    company_name = company_info.get("name", company_info.get("companyName", "N/A"))
    user_info = company_info.get("user", company_info.get("email", "N/A"))

    print(f"OK - Token valide")

    # Résultats
    print("\n" + "=" * 60)
    print("RESULTATS DU TEST")
    print("=" * 60)
    print(f"Entreprise : {company_name}")
    print(f"Utilisateur: {user_info}")
    print(f"\nReponse complete:")
    for key, value in company_info.items():
        print(f"  {key}: {value}")
    print("\nTest reussi !")
    print("=" * 60)


if __name__ == '__main__':
    test_pdp_token()
