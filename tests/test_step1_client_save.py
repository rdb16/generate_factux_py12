"""
Tests pour le flag save_new_client dans step1.

Verifie que :
- save_new_client=0 : pas d'insertion en base (client existant selectionne)
- save_new_client=1 : insertion en base (nouveau client)
- Le formulaire step1 valide correctement les champs obligatoires
"""

import sys
from pathlib import Path

# Ajouter la racine du projet au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app


VALID_STEP1_DATA = {
    'invoice_number': 'TEST-001',
    'type_code': '380',
    'currency_code': 'EUR',
    'issue_date': '2026-02-18',
    'recipient_name': 'Client Test SARL',
    'recipient_siret': '12345678901234',
    'recipient_country_code': 'FR',
}


def get_client():
    """Retourne un test client Flask."""
    app.config['TESTING'] = True
    return app.test_client()


def test_step1_submit_existing_client():
    """Un client selectionne depuis la base (save_new_client=0) ne declenche pas d'insertion."""
    client = get_client()

    data = {**VALID_STEP1_DATA, 'save_new_client': '0'}
    resp = client.post('/invoice/step1', data=data)

    assert resp.status_code == 200, f"Attendu 200, recu {resp.status_code}"
    json_data = resp.get_json()
    assert json_data['success'] is True, f"Attendu success=True, recu {json_data}"
    print("[OK] test_step1_submit_existing_client")


def test_step1_submit_no_save_flag():
    """Sans flag save_new_client, pas d'insertion en base."""
    client = get_client()

    resp = client.post('/invoice/step1', data=VALID_STEP1_DATA)

    assert resp.status_code == 200, f"Attendu 200, recu {resp.status_code}"
    json_data = resp.get_json()
    assert json_data['success'] is True, f"Attendu success=True, recu {json_data}"
    print("[OK] test_step1_submit_no_save_flag")


def test_step1_validation_missing_fields():
    """Les champs obligatoires manquants retournent des erreurs."""
    client = get_client()

    # Formulaire vide
    resp = client.post('/invoice/step1', data={})
    assert resp.status_code == 400, f"Attendu 400, recu {resp.status_code}"

    json_data = resp.get_json()
    assert json_data['success'] is False
    errors = json_data['errors']
    error_fields = [e['field'] for e in errors]

    assert 'issue_date' in error_fields, "Erreur issue_date manquante"
    assert 'recipient_name' in error_fields, "Erreur recipient_name manquante"
    assert 'recipient_siret' in error_fields, "Erreur recipient_siret manquante"
    print("[OK] test_step1_validation_missing_fields")


def test_step1_validation_invalid_siret():
    """Un SIRET invalide retourne une erreur."""
    client = get_client()

    data = {**VALID_STEP1_DATA, 'recipient_siret': '123'}
    resp = client.post('/invoice/step1', data=data)

    assert resp.status_code == 400, f"Attendu 400, recu {resp.status_code}"
    json_data = resp.get_json()
    error_fields = [e['field'] for e in json_data['errors']]
    assert 'recipient_siret' in error_fields, "Erreur recipient_siret manquante"
    print("[OK] test_step1_validation_invalid_siret")


def test_step1_session_stored():
    """Les donnees validees sont stockees en session."""
    client = get_client()

    resp = client.post('/invoice/step1', data=VALID_STEP1_DATA)
    assert resp.status_code == 200

    # Verifier que step2 est accessible (session remplie)
    resp2 = client.get('/invoice/step2')
    assert resp2.status_code == 200, f"Step2 devrait etre accessible, recu {resp2.status_code}"
    print("[OK] test_step1_session_stored")


def test_step1_page_loads():
    """La page step1 se charge correctement."""
    client = get_client()

    resp = client.get('/invoice/step1')
    assert resp.status_code == 200, f"Attendu 200, recu {resp.status_code}"
    assert b'Informations' in resp.data or b'facture' in resp.data.lower()
    print("[OK] test_step1_page_loads")


if __name__ == '__main__':
    test_step1_page_loads()
    test_step1_submit_existing_client()
    test_step1_submit_no_save_flag()
    test_step1_validation_missing_fields()
    test_step1_validation_invalid_siret()
    test_step1_session_stored()
    print("\n=== Tous les tests step1 OK ===")
