"""
Script de test pour vérifier la génération de PDF Factur-X.

Usage: uv run python test_facturx.py
"""

from datetime import datetime
from pathlib import Path

from facturx_generator import generate_facturx_xml
from pdf_generator import generate_invoice_pdf
from facturx import generate_from_binary


def test_facturx_generation():
    """Teste la génération complète d'un PDF Factur-X."""

    # Données de test
    test_data = {
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
            'invoice_number': 'TEST-2026-001',
            'type_code': '380',
            'currency_code': 'EUR',
            'issue_date': '2026-02-05',
            'due_date': '2026-03-05',
            'buyer_reference': 'CLIENT-REF-001',
            'purchase_order_reference': 'PO-2026-001',
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
                'description': 'Développement logiciel - 10 jours',
                'quantity': '10',
                'unit_price_ht': '500',
                'vat_rate': '20',
                'discount_value': '0',
                'discount_type': 'percent',
            },
            {
                'description': 'Support technique - 5 heures',
                'quantity': '5',
                'unit_price_ht': '120',
                'vat_rate': '20',
                'discount_value': '10',
                'discount_type': 'percent',
            },
        ]
    }

    print("=" * 60)
    print("TEST GÉNÉRATION PDF FACTUR-X")
    print("=" * 60)

    # 1. Générer le PDF de base
    print("\n[1/4] Génération du PDF de base avec ReportLab...")
    pdf_bytes = generate_invoice_pdf(test_data, logo_path='./resources/logos/underwork.jpeg')
    print(f"✓ PDF généré: {len(pdf_bytes)} bytes")

    # 2. Générer le XML Factur-X
    print("\n[2/4] Génération du XML Factur-X...")
    xml_content = generate_facturx_xml(test_data)
    print(f"✓ XML généré: {len(xml_content)} caractères")

    # 3. Combiner le PDF et le XML
    print("\n[3/4] Combinaison PDF + XML avec factur-x...")
    facturx_pdf_bytes = generate_from_binary(
        pdf_file=pdf_bytes,
        xml=xml_content.encode('utf-8'),
        flavor='factur-x',
        level='basic',
        check_xsd=True,
        pdf_metadata={
            'author': test_data['emitter']['name'],
            'title': f"Facture {test_data['invoice']['invoice_number']}",
            'subject': 'Facture électronique Factur-X',
        }
    )
    print(f"✓ PDF Factur-X généré: {len(facturx_pdf_bytes)} bytes")

    # 4. Sauvegarder dans le répertoire de test
    print("\n[4/4] Sauvegarde du PDF Factur-X...")
    test_dir = Path('./data/test')
    test_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = test_dir / 'test-facturx.pdf'
    xml_path = test_dir / 'test-facturx.xml'

    with open(pdf_path, 'wb') as f:
        f.write(facturx_pdf_bytes)
    print(f"✓ PDF sauvegardé: {pdf_path}")

    with open(xml_path, 'w', encoding='utf-8') as f:
        f.write(xml_content)
    print(f"✓ XML sauvegardé: {xml_path}")

    # Vérification
    print("\n" + "=" * 60)
    print("RÉSULTATS DU TEST")
    print("=" * 60)
    print(f"PDF de base:     {len(pdf_bytes):,} bytes".replace(',', ' '))
    print(f"XML Factur-X:    {len(xml_content):,} caractères".replace(',', ' '))
    print(f"PDF Factur-X:    {len(facturx_pdf_bytes):,} bytes".replace(',', ' '))
    print(f"\nFichiers générés:")
    print(f"  - {pdf_path}")
    print(f"  - {xml_path}")
    print("\n✓ Test réussi ! Vous pouvez ouvrir le PDF avec un lecteur PDF.")
    print("=" * 60)


if __name__ == '__main__':
    test_facturx_generation()
