"""
Client pour l'API SuperPDP : authentification OAuth2 et envoi de factures.
"""

import json
import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv


def _load_env():
    """Charge .env.local (prioritaire) ou .env depuis la racine du projet."""
    project_root = Path(__file__).resolve().parent.parent
    env_local = project_root / ".env.local"
    env_file = project_root / ".env"

    if env_local.exists():
        load_dotenv(env_local, override=True)
    elif env_file.exists():
        load_dotenv(env_file, override=True)


def get_pdp_token() -> str:
    """
    Récupère un token OAuth2 auprès de l'API SuperPDP.

    Lit PDP_SENDER_ID et PDP_SENDER_SECRET depuis .env / .env.local,
    construit et exécute la commande curl, puis retourne le token.

    Returns:
        Le token OAuth2 (access_token).

    Raises:
        EnvironmentError: Si PDP_SENDER_ID ou PDP_SENDER_SECRET manquent.
        RuntimeError: Si la commande curl échoue ou si la réponse est invalide.
    """
    _load_env()

    sender_id = os.environ.get("PDP_SENDER_ID")
    sender_secret = os.environ.get("PDP_SENDER_SECRET")

    if not sender_id or not sender_secret:
        raise EnvironmentError(
            "PDP_SENDER_ID et PDP_SENDER_SECRET doivent être définis "
            "dans .env ou .env.local"
        )

    curl_cmd = [
        "curl", "-s", "-X", "POST",
        "https://api.superpdp.tech/oauth2/token",
        "-H", "Content-Type: application/x-www-form-urlencoded",
        "-d", (
            f"grant_type=client_credentials"
            f"&client_id={sender_id}"
            f"&client_secret={sender_secret}"
        ),
    ]

    try:
        result = subprocess.run(
            curl_cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Timeout lors de l'appel à l'API SuperPDP (30s)")
    except FileNotFoundError:
        raise RuntimeError("curl n'est pas installé ou introuvable dans le PATH")

    if result.returncode != 0:
        raise RuntimeError(
            f"Erreur curl (code {result.returncode}): {result.stderr.strip()}"
        )

    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(
            f"Réponse invalide de l'API SuperPDP: {result.stdout[:200]}"
        )

    if "error" in response:
        raise RuntimeError(
            f"Erreur API SuperPDP: {response.get('error')} "
            f"- {response.get('error_description', '')}"
        )

    oauth_token = response.get("access_token")
    if not oauth_token:
        raise RuntimeError(
            f"Pas de access_token dans la réponse: {result.stdout[:200]}"
        )

    return oauth_token
