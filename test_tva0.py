"""
Test de génération Factur-X avec TVA 0% et catégories d'exonération.
Vérifie le XML (CategoryCode, BT-120, BT-121) et le PDF.

Usage: uv run python test_tva0.py
"""

from facturx_generator import generate_facturx_xml
from pdf_generator import generate_invoice_pdf
from pathlib import Path


def test_data():
    return {
        'emitter': {
            'name': 'ACME Corporation',
            'address': '123 rue de la Paix',
            'postal_code': '75001',
            'city': 'Paris',
            'country_code': 'FR',
            'siren': '123456789',
            'siret': '12345678901234',
            'vat_number': 'FR12345678901',
            'bic': 'BNPAFRPPXXX',
        },
        'invoice': {
            'invoice_number': 'TEST-TVA0-001',
            'type_code': '380',
            'currency_code': 'EUR',
            'issue_date': '2026-02-10',
            'due_date': '2026-03-10',
            'buyer_reference': 'REF-001',
            'purchase_order_reference': 'PO-001',
            'payment_terms': 'Paiement sous 30 jours',
            'recipient_name': 'Client Test SAS',
            'recipient_siret': '98765432109876',
            'recipient_vat_number': 'FR98765432109',
            'recipient_address': '456 avenue des Champs',
            'recipient_postal_code': '75008',
            'recipient_city': 'Paris',
            'recipient_country_code': 'FR',
        },
        'lines': [
            {
                'description': 'Prestation de conseil - 5 jours',
                'quantity': '5',
                'unit_price_ht': '800',
                'vat_rate': '20',
                'discount_value': '0',
                'discount_type': 'percent',
            },
            {
                'description': 'Formation professionnelle (exoneree TVA)',
                'quantity': '3',
                'unit_price_ht': '500',
                'vat_rate': '0',
                'vat_category': 'E',
                'vat_exemption_code': 'VATEX-FR-FRANCHISE',
                'vat_exemption_reason': 'Franchise en base de TVA',
                'discount_value': '0',
                'discount_type': 'percent',
            },
        ]
    }


def test_xml():
    """Test 1 : XML avec CategoryCode E et BT-120/BT-121."""
    print("=" * 60)
    print("TEST 1 — XML Factur-X avec TVA 0% categorie E")
    print("=" * 60)

    data = test_data()
    xml = generate_facturx_xml(data)

    checks = {
        'CategoryCode S (ligne 20%)': '>S<' in xml,
        'CategoryCode E (ligne 0%)': '>E<' in xml,
        'ExemptionReason present': '<ram:ExemptionReason>' in xml,
        'ExemptionReasonCode present': '<ram:ExemptionReasonCode>' in xml,
        'VATEX-FR-FRANCHISE dans XML': 'VATEX-FR-FRANCHISE' in xml,
        'Franchise en base dans XML': 'Franchise en base de TVA' in xml,
        'Pas de CategoryCode Z': '>Z<' not in xml,
    }

    all_ok = True
    for label, result in checks.items():
        status = 'OK' if result else 'FAIL'
        if not result:
            all_ok = False
        print(f"  [{status}] {label}")

    # Afficher l'extrait XML pertinent
    print("\n--- Extrait XML (header ApplicableTradeTax) ---")
    in_tax = False
    for line in xml.split('\n'):
        if '<ram:ApplicableTradeTax>' in line and not in_tax:
            # Chercher le header-level (pas dans IncludedSupplyChainTradeLineItem)
            in_tax = True
        if in_tax:
            print(line)
        if '</ram:ApplicableTradeTax>' in line and in_tax:
            in_tax = False

    return all_ok


def test_xml_zero_rate_z():
    """Test 2 : XML avec CategoryCode Z (pas de motif requis)."""
    print("\n" + "=" * 60)
    print("TEST 2 — XML Factur-X avec TVA 0% categorie Z")
    print("=" * 60)

    data = test_data()
    data['lines'][1] = {
        'description': 'Produit taux zero',
        'quantity': '2',
        'unit_price_ht': '100',
        'vat_rate': '0',
        'vat_category': 'Z',
        'vat_exemption_code': '',
        'vat_exemption_reason': '',
        'discount_value': '0',
        'discount_type': 'percent',
    }

    xml = generate_facturx_xml(data)

    checks = {
        'CategoryCode Z present': '>Z<' in xml,
        'Pas de ExemptionReason': '<ram:ExemptionReason>' not in xml,
        'Pas de ExemptionReasonCode': '<ram:ExemptionReasonCode>' not in xml,
    }

    all_ok = True
    for label, result in checks.items():
        status = 'OK' if result else 'FAIL'
        if not result:
            all_ok = False
        print(f"  [{status}] {label}")

    return all_ok


def test_pdf():
    """Test 3 : PDF avec colonne TVA affichant la categorie."""
    print("\n" + "=" * 60)
    print("TEST 3 — PDF avec categorie TVA dans colonne")
    print("=" * 60)

    data = test_data()
    pdf_bytes = generate_invoice_pdf(data, logo_path='./resources/logos/underwork.jpeg')

    test_dir = Path('./data/test')
    test_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = test_dir / 'test-tva0.pdf'
    with open(pdf_path, 'wb') as f:
        f.write(pdf_bytes)

    print(f"  [OK] PDF genere: {pdf_path} ({len(pdf_bytes)} bytes)")
    print("  [INFO] Ouvrez le PDF pour verifier : colonne TVA affiche '0,00 (E)' et motif dans recap")

    return True


def test_mixed_invoice():
    """Test 4 : Facture mixte avec 2 groupes TVA distincts dans le XML."""
    print("\n" + "=" * 60)
    print("TEST 4 — Facture mixte : 20% + 0% (E) = 2 groupes TVA")
    print("=" * 60)

    data = test_data()
    xml = generate_facturx_xml(data)

    # Compter les blocs ApplicableTradeTax dans le header settlement
    # (pas ceux dans les lignes)
    header_tax_count = 0
    in_settlement = False
    for line in xml.split('\n'):
        if 'ApplicableHeaderTradeSettlement' in line:
            in_settlement = True
        if in_settlement and '<ram:ApplicableTradeTax>' in line:
            header_tax_count += 1
        if 'SpecifiedTradePaymentTerms' in line:
            in_settlement = False

    checks = {
        '2 blocs ApplicableTradeTax dans header': header_tax_count == 2,
    }

    all_ok = True
    for label, result in checks.items():
        status = 'OK' if result else 'FAIL'
        if not result:
            all_ok = False
        print(f"  [{status}] {label} (trouve: {header_tax_count})")

    return all_ok


if __name__ == '__main__':
    results = []
    results.append(('XML categorie E + BT-120/BT-121', test_xml()))
    results.append(('XML categorie Z sans motif', test_xml_zero_rate_z()))
    results.append(('PDF avec categorie', test_pdf()))
    results.append(('Facture mixte 2 groupes', test_mixed_invoice()))

    print("\n" + "=" * 60)
    print("RESULTAT FINAL")
    print("=" * 60)
    all_passed = True
    for name, passed in results:
        status = 'PASS' if passed else 'FAIL'
        if not passed:
            all_passed = False
        print(f"  [{status}] {name}")

    print(f"\n{'Tous les tests passent !' if all_passed else 'Des tests ont echoue.'}")
