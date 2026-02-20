"""
Client pour l'API SuperPDP : authentification OAuth2 et envoi de factures.
"""

import json
import os
import subprocess
import time
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_TOKEN_CACHE_PATH = _PROJECT_ROOT / ".pdp_token_cache.json"


def _load_env():
    """Charge .env.local (prioritaire) ou .env depuis la racine du projet."""
    project_root = Path(__file__).resolve().parent.parent
    env_local = project_root / ".env.local"
    env_file = project_root / ".env"

    if env_local.exists():
        load_dotenv(env_local, override=True)
    elif env_file.exists():
        load_dotenv(env_file, override=True)


def get_pdp_token() -> dict:
    """
    Récupère un token OAuth2 auprès de l'API SuperPDP.

    Lit PDP_SENDER_ID et PDP_SENDER_SECRET depuis .env / .env.local,
    construit et exécute la commande curl, puis retourne la réponse JSON complète.

    Returns:
        Dictionnaire JSON : {access_token, expires_in, scope, token_type}.

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

    if "access_token" not in response:
        raise RuntimeError(
            f"Pas de access_token dans la réponse: {result.stdout[:200]}"
        )

    return response


def get_cached_pdp_token() -> dict:
    """
    Retourne un token OAuth2 SuperPDP depuis le cache local ou via l'API.

    Lit le fichier cache `.pdp_token_cache.json` à la racine du projet.
    Si le token est encore valide (avec une marge de 60 s), il est retourné
    directement sans appel réseau. Sinon, un nouveau token est demandé via
    `get_pdp_token()` et le cache est mis à jour.

    Returns:
        Dictionnaire JSON : {access_token, expires_in, token_type, fetched_at}.
    """
    if _TOKEN_CACHE_PATH.exists():
        try:
            cached = json.loads(_TOKEN_CACHE_PATH.read_text(encoding="utf-8"))
            fetched_at = cached.get("fetched_at", 0)
            expires_in = cached.get("expires_in", 0)
            if fetched_at + expires_in - 60 > time.time():
                return cached
        except (json.JSONDecodeError, OSError):
            pass

    token_data = get_pdp_token()
    token_data["fetched_at"] = time.time()
    _TOKEN_CACHE_PATH.write_text(
        json.dumps(token_data, indent=2), encoding="utf-8"
    )
    return token_data


def send_facturx_to_pdp(pdf_path: str) -> dict:
    """
    Envoie un PDF Factur-X à l'API SuperPDP.

    Args:
        pdf_path: Chemin vers le fichier PDF Factur-X à envoyer.

    Returns:
        Dictionnaire JSON de la réponse API.

    Raises:
        FileNotFoundError: Si le fichier PDF n'existe pas.
        RuntimeError: Si la commande curl échoue ou si la réponse est invalide.
    """
    pdf = Path(pdf_path)
    if not pdf.exists():
        raise FileNotFoundError(f"Fichier PDF introuvable : {pdf_path}")

    token_data = get_cached_pdp_token()
    access_token = token_data["access_token"]

    curl_cmd = [
        "curl", "-s", "-X", "POST",
        "https://api.superpdp.tech/v1.beta/invoices",
        "-H", f"Authorization: Bearer {access_token}",
        "-H", "Content-Type: application/pdf",
        "--data-binary", f"@{pdf}",
    ]

    try:
        result = subprocess.run(
            curl_cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Timeout lors de l'envoi de la facture (30s)")
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
            f"- {response.get('error_description', response.get('message', ''))}"
        )

    return response


def check_pdp_token(token: str) -> dict:
    """
    Vérifie la validité d'un token OAuth2 auprès de l'API SuperPDP.

    Appelle GET /v1.beta/companies/me avec le Bearer token
    et retourne les informations de l'entreprise associée.

    Args:
        token: Le token OAuth2 obtenu via get_pdp_token().

    Returns:
        Le dictionnaire JSON de la réponse API (infos entreprise).

    Raises:
        ValueError: Si le token est vide ou None.
        RuntimeError: Si la commande curl échoue ou si la réponse est invalide.
    """
    if not token:
        raise ValueError("Le token OAuth2 ne peut pas être vide")

    curl_cmd = [
        "curl", "-s",
        "https://api.superpdp.tech/v1.beta/companies/me",
        "-H", f"Authorization: Bearer {token}",
    ]

    try:
        result = subprocess.run(
            curl_cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Timeout lors de la vérification du token (30s)")
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
            f"- {response.get('error_description', response.get('message', ''))}"
        )

    return response
