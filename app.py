"""
Application Flask pour générer des factures au format Factur-X.
"""

from datetime import datetime
from decimal import Decimal
from flask import Flask, render_template, request, jsonify, session, Response
from pathlib import Path
import re

from facturx_generator import generate_facturx_xml

app = Flask(__name__, template_folder='resources/templates', static_folder='resources')
app.secret_key = 'facturx-secret-key-change-in-production'

# Configuration de l'émetteur (à personnaliser)
EMITTER = {
    'name': 'Mon Entreprise SARL',
    'address': '12 rue de la Paix',
    'postal_code': '75001',
    'city': 'Paris',
    'country_code': 'FR',
    'siret': '12345678900012',
    'vat_number': 'FR12345678901',
}

TYPE_LABELS = {
    '380': 'Facture',
    '381': 'Avoir',
    '384': 'Facture rectificative',
    '389': 'Facture d\'acompte',
}


def validate_step1(data: dict) -> list[dict]:
    """Valide les données du formulaire step1."""
    errors = []

    if not data.get('invoice_number', '').strip():
        errors.append({'field': 'invoice_number', 'message': 'Le numéro de facture est obligatoire'})

    if not data.get('issue_date'):
        errors.append({'field': 'issue_date', 'message': 'La date d\'émission est obligatoire'})

    if not data.get('recipient_name', '').strip():
        errors.append({'field': 'recipient_name', 'message': 'La raison sociale du client est obligatoire'})

    siret = data.get('recipient_siret', '').strip()
    if not siret:
        errors.append({'field': 'recipient_siret', 'message': 'Le SIRET du client est obligatoire'})
    elif not re.match(r'^\d{14}$', siret):
        errors.append({'field': 'recipient_siret', 'message': 'Le SIRET doit contenir exactement 14 chiffres'})

    if not data.get('recipient_country_code'):
        errors.append({'field': 'recipient_country_code', 'message': 'Le pays du client est obligatoire'})

    return errors


def validate_step2(lines: list[dict]) -> list[dict]:
    """Valide les lignes de facture."""
    errors = []

    if not lines:
        errors.append({'field': 'lines', 'message': 'La facture doit contenir au moins une ligne'})
        return errors

    for i, line in enumerate(lines):
        if not line.get('description', '').strip():
            errors.append({
                'field': f'lines[{i}][description]',
                'message': f'Ligne {i+1} : la description est obligatoire'
            })

        try:
            qty = Decimal(str(line.get('quantity', 0)))
            if qty <= 0:
                errors.append({
                    'field': f'lines[{i}][quantity]',
                    'message': f'Ligne {i+1} : la quantité doit être supérieure à 0'
                })
        except (ValueError, TypeError):
            errors.append({
                'field': f'lines[{i}][quantity]',
                'message': f'Ligne {i+1} : quantité invalide'
            })

        try:
            price = Decimal(str(line.get('unit_price_ht', 0)))
            if price <= 0:
                errors.append({
                    'field': f'lines[{i}][unit_price_ht]',
                    'message': f'Ligne {i+1} : le prix unitaire doit être supérieur à 0'
                })
        except (ValueError, TypeError):
            errors.append({
                'field': f'lines[{i}][unit_price_ht]',
                'message': f'Ligne {i+1} : prix unitaire invalide'
            })

    return errors


def parse_lines_from_form(form_data) -> list[dict]:
    """Parse les lignes de facture depuis les données du formulaire."""
    lines = []
    line_indices = set()

    for key in form_data.keys():
        if key.startswith('lines[') and '][' in key:
            idx = int(key.split('[')[1].split(']')[0])
            line_indices.add(idx)

    for idx in sorted(line_indices):
        line = {
            'description': form_data.get(f'lines[{idx}][description]', ''),
            'quantity': form_data.get(f'lines[{idx}][quantity]', ''),
            'unit_price_ht': form_data.get(f'lines[{idx}][unit_price_ht]', ''),
            'vat_rate': form_data.get(f'lines[{idx}][vat_rate]', '20'),
            'discount_value': form_data.get(f'lines[{idx}][discount_value]', ''),
            'discount_type': form_data.get(f'lines[{idx}][discount_type]', 'percent'),
        }
        lines.append(line)

    return lines


def format_date_display(date_str: str) -> str:
    """Formate une date pour l'affichage."""
    if not date_str:
        return ''
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%d/%m/%Y')
    except ValueError:
        return date_str


@app.route('/')
def index():
    """Affiche le formulaire step1."""
    return render_template(
        'invoice_step1.html',
        logo_path='/logos/sntpk-logo.jpeg',
        emitter=EMITTER,
    )


@app.route('/invoice/step1', methods=['POST'])
def submit_step1():
    """Traite le formulaire step1 et stocke les données en session."""
    data = {
        'invoice_number': request.form.get('invoice_number', ''),
        'type_code': request.form.get('type_code', '380'),
        'currency_code': request.form.get('currency_code', 'EUR'),
        'issue_date': request.form.get('issue_date', ''),
        'due_date': request.form.get('due_date', ''),
        'buyer_reference': request.form.get('buyer_reference', ''),
        'purchase_order_reference': request.form.get('purchase_order_reference', ''),
        'payment_terms': request.form.get('payment_terms', ''),
        'recipient_name': request.form.get('recipient_name', ''),
        'recipient_siret': request.form.get('recipient_siret', ''),
        'recipient_vat_number': request.form.get('recipient_vat_number', ''),
        'recipient_address': request.form.get('recipient_address', ''),
        'recipient_country_code': request.form.get('recipient_country_code', 'FR'),
    }

    errors = validate_step1(data)

    if errors:
        return jsonify({'success': False, 'errors': errors}), 400

    # Stocker en session
    session['invoice_data'] = data

    return jsonify({'success': True})


@app.route('/invoice/step2')
def show_step2():
    """Affiche le formulaire step2 avec les données de step1."""
    invoice_data = session.get('invoice_data')

    if not invoice_data:
        return render_template(
            'invoice_step1.html',
            logo_path='/logos/sntpk-logo.jpeg',
            emitter=EMITTER,
        )

    invoice = {
        **invoice_data,
        'type_label': TYPE_LABELS.get(invoice_data['type_code'], 'Facture'),
        'issue_date_display': format_date_display(invoice_data['issue_date']),
        'due_date_display': format_date_display(invoice_data['due_date']),
    }

    return render_template(
        'invoice_step2.html',
        logo_path='/logos/sntpk-logo.jpeg',
        emitter=EMITTER,
        invoice=invoice,
    )


@app.route('/invoice', methods=['POST'])
def generate_invoice():
    """Génère le fichier XML Factur-X."""
    invoice_data = session.get('invoice_data')

    if not invoice_data:
        return jsonify({
            'success': False,
            'errors': [{'field': '_form', 'message': 'Session expirée, veuillez recommencer'}]
        }), 400

    lines = parse_lines_from_form(request.form)
    errors = validate_step2(lines)

    if errors:
        return jsonify({'success': False, 'errors': errors}), 400

    # Préparer les données complètes pour la génération
    full_data = {
        'emitter': EMITTER,
        'invoice': invoice_data,
        'lines': lines,
    }

    # Générer le XML Factur-X
    xml_content = generate_facturx_xml(full_data)

    # Retourner le XML en téléchargement
    filename = f"facturx-{invoice_data['invoice_number']}.xml"

    return Response(
        xml_content,
        mimetype='application/xml',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
    )


if __name__ == '__main__':
    app.run(debug=True, port=5000)
