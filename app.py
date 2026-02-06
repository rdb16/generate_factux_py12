"""
Application Flask pour générer des factures au format Factur-X.
"""

import atexit
import os
import sys
from datetime import datetime
from decimal import Decimal
from flask import Flask, render_template, request, jsonify, session, Response
from pathlib import Path
import re

from facturx_generator import generate_facturx_xml
from pdf_generator import generate_invoice_pdf
from facturx import generate_from_binary

# Variable globale pour la connexion DB (si PostgreSQL activé)
db_connection = None


def load_config(config_path: str = 'resources/config/ma-conf.txt') -> dict:
    """Charge la configuration depuis un fichier texte."""
    config = {}
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Fichier de configuration introuvable: {config_path}")

    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                # Conversion des booléens
                if value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
                config[key] = value

    return config




def validate_emitter_config(config: dict) -> list[str]:
    """Valide les champs obligatoires de l'émetteur."""
    errors = []

    # Validation SIRET (14 chiffres)
    siret = config.get('siret', '')
    if not siret:
        errors.append("SIRET de l'émetteur non renseigné dans la configuration")
    elif not re.match(r'^\d{14}$', siret):
        errors.append(f"SIRET de l'émetteur invalide: '{siret}' (doit contenir 14 chiffres)")

    # Validation SIREN (9 chiffres)
    siren = config.get('siren', '')
    if not siren:
        errors.append("SIREN de l'émetteur non renseigné dans la configuration")
    elif not re.match(r'^\d{9}$', siren):
        errors.append(f"SIREN de l'émetteur invalide: '{siren}' (doit contenir 9 chiffres)")

    # Validation cohérence SIREN/SIRET
    if siret and siren and not siret.startswith(siren):
        errors.append(f"Incohérence SIREN/SIRET: le SIRET '{siret}' devrait commencer par le SIREN '{siren}'")

    # Validation BIC (8 ou 11 caractères alphanumériques)
    bic = config.get('bic', '')
    if bic and not re.match(r'^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$', bic.upper()):
        errors.append(f"BIC invalide: '{bic}' (format attendu: 8 ou 11 caractères)")

    # Validation numéro TVA intracommunautaire (format FR + 11 caractères)
    num_tva = config.get('num_tva', '')
    if num_tva and not re.match(r'^[A-Z]{2}[A-Z0-9]{2,13}$', num_tva.upper()):
        errors.append(f"Numéro TVA invalide: '{num_tva}' (format attendu: code pays + identifiant)")

    # Validation nom obligatoire
    if not config.get('name', '').strip():
        errors.append("Nom de l'émetteur non renseigné dans la configuration")

    return errors


def get_logo_path(config: dict) -> str:
    """Retourne le chemin du logo, avec fallback sur underwork.jpeg."""
    logo = config.get('logo', '').strip()

    if not logo:
        # Logo par défaut
        return './resources/logos/underwork.jpeg'

    # Vérifier que le fichier existe
    logo_path = Path(logo)
    if not logo_path.exists():
        print(f"[WARNING] Logo introuvable: {logo}, utilisation du logo par défaut")
        return './resources/logos/underwork.jpeg'

    return logo


def load_env_file() -> dict:
    """Charge les variables d'environnement depuis .env ou .env.local."""
    env_vars = {}

    # Chercher .env.local en priorité, sinon .env
    env_file = None
    for filename in ['.env.local', '.env']:
        path = Path(filename)
        if path.exists():
            env_file = path
            break

    if env_file is None:
        return env_vars

    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                env_vars[key] = value
                os.environ[key] = value

    return env_vars


def check_database_connection(config: dict) -> bool:
    """Vérifie la connexion à la base de données PostgreSQL."""
    global db_connection

    try:
        import psycopg2
    except ImportError:
        print("[ERROR] Le module psycopg2 n'est pas installé. Exécutez: uv add psycopg2-binary")
        return False

    # Récupérer les paramètres de connexion depuis les variables d'environnement
    db_host = os.environ.get('DB_URL', 'localhost')
    db_port = os.environ.get('DB_PORT', '5432')
    db_name = os.environ.get('DB_NAME', 'k_factur_x')
    db_user = os.environ.get('DB_USER', 'postgres')
    db_password = os.environ.get('DB_PASS', '')

    try:
        db_connection = psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=db_user,
            password=db_password
        )
        db_connection.autocommit = False
        print(f"[OK] Connexion à PostgreSQL établie ({db_host}:{db_port}/{db_name})")
        return True
    except psycopg2.Error as e:
        print(f"[ERROR] Impossible de se connecter à PostgreSQL: {e}")
        return False


def close_database_connection():
    """Ferme proprement la connexion PostgreSQL."""
    global db_connection
    if db_connection and not db_connection.closed:
        db_connection.close()
        print("[OK] Connexion PostgreSQL fermée")


atexit.register(close_database_connection)


def get_next_invoice_number() -> str:
    """Calcule le prochain numéro de facture depuis la base (sans lock)."""
    global db_connection
    now = datetime.now()

    cursor = db_connection.cursor()
    cursor.execute(
        "SELECT invoice_num FROM sent_invoices ORDER BY created_at DESC LIMIT 1"
    )
    row = cursor.fetchone()
    cursor.close()

    if row is None:
        return f"FAC-{now.year}-{now.month:02d}-00001"

    last_number = row[0]
    match = re.match(r'^FAC-\d{4}-\d{2}-(\d+)$', last_number)
    if match:
        next_int = int(match.group(1)) + 1
    else:
        next_int = 1

    return f"FAC-{now.year}-{now.month:02d}-{next_int:05d}"


def insert_sent_invoice(invoice_num: str, company_name: str, company_siret: str,
                        xml_content: str, pdf_path: str, invoice_date: str) -> None:
    """Insère la facture dans sent_invoices (dans la transaction en cours)."""
    global db_connection
    cursor = db_connection.cursor()
    cursor.execute(
        """INSERT INTO sent_invoices
           (invoice_num, company_name, company_siret, xml_facture, pdf_path, invoice_date)
           VALUES (%s, %s, %s, %s::xml, %s, %s)""",
        (invoice_num, company_name, company_siret, xml_content, pdf_path, invoice_date),
    )
    cursor.close()


def ensure_storage_directories(config: dict) -> None:
    """Crée les répertoires de stockage s'ils n'existent pas."""
    xml_storage = config.get('xml_storage', './data/factures-xml')
    pdf_storage = config.get('pdf_storage', './data/factures-pdf')

    for storage_path in [xml_storage, pdf_storage]:
        path = Path(storage_path)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            print(f"[OK] Répertoire créé: {storage_path}")


def validate_startup_config() -> None:
    """Valide la configuration au démarrage de l'application."""
    print("=" * 60)
    print("Validation de la configuration...")
    print("=" * 60)

    errors = []

    # 1. Valider les champs émetteur
    emitter_errors = validate_emitter_config(CONFIG)
    errors.extend(emitter_errors)

    # 2. Vérifier le fichier .env si PostgreSQL activé
    if CONFIG.get('is_db_pg') is True:
        env_file_exists = Path('.env').exists() or Path('.env.local').exists()
        if not env_file_exists:
            errors.append("is_db_pg=True mais aucun fichier .env ou .env.local trouvé")
        else:
            # Charger les variables d'environnement
            load_env_file()

            # 3. Vérifier la connexion à la base
            if not check_database_connection(CONFIG):
                errors.append("Impossible d'établir la connexion à PostgreSQL")

    # 4. Créer les répertoires de stockage
    ensure_storage_directories(CONFIG)

    # Afficher les résultats
    if errors:
        print("\n[ERREURS DE CONFIGURATION]")
        for error in errors:
            print(f"  - {error}")
        print("\nL'application ne peut pas démarrer. Corrigez les erreurs ci-dessus.")
        sys.exit(1)
    else:
        print("\n[OK] Configuration validée avec succès")
        print(f"  - Émetteur: {CONFIG.get('name')}")
        print(f"  - SIRET: {CONFIG.get('siret')}")
        print(f"  - Logo: {LOGO_PATH}")
        print(f"  - PostgreSQL: {'Activé' if CONFIG.get('is_db_pg') else 'Désactivé'}")
        if CONFIG.get('is_db_pg') is True and CONFIG.get('is_num_facturx_auto') is True:
            try:
                next_num = get_next_invoice_number()
                print(f"  - Numérotation auto: Activée (prochain: {next_num})")
            except Exception as e:
                print(f"  - Numérotation auto: [ERREUR] {e}")
        elif CONFIG.get('is_num_facturx_auto') is True:
            print("  - Numérotation auto: Désactivée (requiert is_db_pg=True)")
        print(f"  - Stockage XML: {CONFIG.get('xml_storage', './data/factures-xml')}")
    print("=" * 60 + "\n")


# Charger la configuration
CONFIG = load_config()

# Définir le chemin du logo (avec fallback)
LOGO_PATH = get_logo_path(CONFIG)

# Configuration de l'émetteur depuis le fichier de config
EMITTER = {
    'name': CONFIG.get('name', ''),
    'address': CONFIG.get('address', ''),
    'postal_code': CONFIG.get('postal_code', ''),
    'city': CONFIG.get('city', ''),
    'country_code': CONFIG.get('country_code', 'FR'),
    'siren': CONFIG.get('siren', ''),
    'siret': CONFIG.get('siret', ''),
    'vat_number': CONFIG.get('num_tva', ''),
    'bic': CONFIG.get('bic', ''),
}

app = Flask(__name__, template_folder='resources/templates', static_folder='resources', static_url_path='/static')
app.secret_key = 'facturx-secret-key-change-in-production'

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


def get_logo_url() -> str:
    """Retourne l'URL du logo pour les templates."""
    logo = LOGO_PATH
    # Flask static_folder='resources', donc les URLs doivent commencer par /static/
    if logo.startswith('./resources/'):
        return '/static/' + logo[len('./resources/'):]
    elif logo.startswith('resources/'):
        return '/static/' + logo[len('resources/'):]
    return logo


@app.route('/')
def index():
    """Affiche le formulaire step1."""
    next_invoice_number = None
    auto_numbering = (
        CONFIG.get('is_db_pg') is True
        and CONFIG.get('is_num_facturx_auto') is True
        and db_connection
        and not db_connection.closed
    )
    if auto_numbering:
        try:
            next_invoice_number = get_next_invoice_number()
        except Exception as e:
            print(f"[WARNING] Impossible de calculer le prochain numéro: {e}")

    return render_template(
        'invoice_step1.html',
        logo_path=get_logo_url(),
        emitter=EMITTER,
        next_invoice_number=next_invoice_number,
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
        'recipient_postal_code': request.form.get('recipient_postal_code', ''),
        'recipient_city': request.form.get('recipient_city', ''),
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
            logo_path=get_logo_url(),
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
        logo_path=get_logo_url(),
        emitter=EMITTER,
        invoice=invoice,
    )


def save_xml_to_storage(xml_content: str, invoice_number: str) -> str:
    """Sauvegarde le XML dans le répertoire de stockage."""
    xml_storage = CONFIG.get('xml_storage', './data/factures-xml')

    # Nettoyer le numéro de facture pour le nom de fichier
    safe_number = re.sub(r'[^\w\-]', '_', invoice_number)
    filename = f"facturx-{safe_number}.xml"
    filepath = Path(xml_storage) / filename

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(xml_content)

    print(f"[OK] XML sauvegardé: {filepath}")
    return str(filepath)


def save_pdf_to_storage(pdf_bytes: bytes, invoice_number: str) -> str:
    """Sauvegarde le PDF Factur-X dans le répertoire de stockage."""
    pdf_storage = CONFIG.get('pdf_storage', './data/factures-pdf')

    # Nettoyer le numéro de facture pour le nom de fichier
    safe_number = re.sub(r'[^\w\-]', '_', invoice_number)
    filename = f"facturx-{safe_number}.pdf"
    filepath = Path(pdf_storage) / filename

    with open(filepath, 'wb') as f:
        f.write(pdf_bytes)

    print(f"[OK] PDF Factur-X sauvegardé: {filepath}")
    return str(filepath)


@app.route('/invoice', methods=['POST'])
def generate_invoice():
    """Génère le fichier PDF Factur-X complet (PDF + XML embarqué)."""
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

    auto_numbering = (
        CONFIG.get('is_db_pg') is True
        and CONFIG.get('is_num_facturx_auto') is True
        and db_connection
        and not db_connection.closed
    )

    try:
        # Si numérotation auto : lock table + calcul du numéro
        if auto_numbering:
            cursor = db_connection.cursor()
            cursor.execute("LOCK TABLE sent_invoices IN EXCLUSIVE MODE")
            cursor.close()
            invoice_data['invoice_number'] = get_next_invoice_number()
            session['invoice_data'] = invoice_data

        # Préparer les données complètes pour la génération
        full_data = {
            'emitter': EMITTER,
            'invoice': invoice_data,
            'lines': lines,
        }

        # 1. Générer le PDF de base avec ReportLab
        pdf_bytes = generate_invoice_pdf(full_data, logo_path=LOGO_PATH)

        # 2. Générer le XML Factur-X
        xml_content = generate_facturx_xml(full_data)

        # 3. Combiner le PDF et le XML avec factur-x
        facturx_pdf_bytes = generate_from_binary(
            pdf_file=pdf_bytes,
            xml=xml_content.encode('utf-8'),
            flavor='factur-x',
            level='basic',
            check_xsd=True,
            pdf_metadata={
                'author': EMITTER['name'],
                'title': f"Facture {invoice_data['invoice_number']}",
                'subject': 'Facture électronique Factur-X',
            }
        )

        # 4. Sauvegarder le XML et le PDF dans le répertoire de stockage
        save_xml_to_storage(xml_content, invoice_data['invoice_number'])
        pdf_filepath = save_pdf_to_storage(facturx_pdf_bytes, invoice_data['invoice_number'])

        # 5. Insérer en base (dans la même transaction que le lock)
        if auto_numbering:
            insert_sent_invoice(
                invoice_num=invoice_data['invoice_number'],
                company_name=invoice_data['recipient_name'],
                company_siret=invoice_data['recipient_siret'],
                xml_content=xml_content,
                pdf_path=pdf_filepath,
                invoice_date=invoice_data['issue_date'],
            )
            db_connection.commit()
            print(f"[OK] Facture {invoice_data['invoice_number']} insérée en base")

    except Exception as e:
        if auto_numbering and db_connection and not db_connection.closed:
            db_connection.rollback()
        print(f"[ERROR] Échec de la génération Factur-X: {e}")
        return jsonify({
            'success': False,
            'errors': [{'field': '_form', 'message': f'Erreur lors de la génération: {str(e)}'}]
        }), 500

    # 6. Retourner le PDF Factur-X en téléchargement
    filename = f"facturx-{invoice_data['invoice_number']}.pdf"

    return Response(
        facturx_pdf_bytes,
        mimetype='application/pdf',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
    )


if __name__ == '__main__':
    # Valider la configuration au démarrage
    validate_startup_config()
    app.run(debug=True, port=5000)
