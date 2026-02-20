"""
Application Flask pour générer des factures au format Factur-X.
"""

import math
import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
from pathlib import Path
import re

from utils.facturx_generator import generate_facturx_xml
from utils.pdf_generator import generate_invoice_pdf
from utils.invoice_calc import calculate_line_totals, calculate_invoice_totals
from utils.db import get_db_connection, db_cursor, db_connection
from utils.super_pdp import get_pdp_token
from facturx import generate_from_binary


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

    # Validation forme juridique obligatoire
    if not config.get('cie_legal_form', '').strip():
        errors.append("Forme juridique (cie_legal_form) non renseignée dans la configuration")

    # Validation IBAN obligatoire
    if not config.get('cie_IBAN', '').strip():
        errors.append("IBAN de l'émetteur (cie_IBAN) non renseigné dans la configuration")

    # Validation texte PMT obligatoire (BR-FR-05)
    if not config.get('pmt_text', '').strip():
        errors.append("Texte frais de recouvrement (pmt_text) non renseigné dans la configuration")

    # Validation texte PMD obligatoire (BR-FR-05)
    if not config.get('pmd_text', '').strip():
        errors.append("Texte pénalités de retard (pmd_text) non renseigné dans la configuration")

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


def check_database_connection() -> bool:
    """Vérifie la connexion à la base de données PostgreSQL (ouvre puis ferme)."""
    try:
        import psycopg2
    except ImportError:
        print("[ERROR] Le module psycopg2 n'est pas installé. Exécutez: uv add psycopg2-binary")
        return False

    db_host = os.environ.get('DB_URL', 'localhost')
    db_port = os.environ.get('DB_PORT', '5432')
    db_name = os.environ.get('DB_NAME', 'k_factur_x')

    try:
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            dbname=db_name,
            user=os.environ.get('DB_USER', 'postgres'),
            password=os.environ.get('DB_PASS', ''),
        )
        print(f"[OK] Connexion à PostgreSQL établie ({db_host}:{db_port}/{db_name})")
        conn.close()
        print("[OK] Connexion PostgreSQL fermée (contrôle démarrage)")
        return True
    except psycopg2.Error as e:
        print(f"[ERROR] Impossible de se connecter à PostgreSQL: {e}")
        return False


def is_auto_numbering() -> bool:
    """Indique si la numérotation automatique est active."""
    return CONFIG.get('is_db_pg') is True and CONFIG.get('is_num_facturx_auto') is True


def get_next_invoice_number(conn) -> str:
    """Calcule le prochain numéro de facture depuis la base."""
    now = datetime.now()

    cursor = conn.cursor()
    cursor.execute(
        "SELECT invoice_num FROM sent_invoices ORDER BY created_at DESC LIMIT 1"
    )
    row = cursor.fetchone()
    cursor.close()

    if row is None:
        return f"FAC-{now.year}-{now.month:02d}-0001"

    last_number = row[0]
    last_part = last_number.rsplit('-', 1)[-1]
    next_int = int(last_part) + 1

    return f"FAC-{now.year}-{now.month:02d}-{next_int:04d}"


def insert_sent_invoice(conn, invoice_num: str, company_name: str, company_siret: str,
                        xml_content: str, pdf_path: str, invoice_date: str,
                        total_ttc=None) -> None:
    """Insère la facture dans sent_invoices (dans la transaction en cours)."""
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO sent_invoices
           (invoice_num, company_name, company_siret, xml_facture, pdf_path, invoice_date, total_ttc)
           VALUES (%s, %s, %s, %s::xml, %s, %s, %s)""",
        (invoice_num, company_name, company_siret, xml_content, pdf_path, invoice_date, total_ttc),
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

            # 3. Vérifier la connexion à la base (ouvre puis ferme)
            if not check_database_connection():
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
        print(f"  - Super PDP (PA): {'Activé' if CONFIG.get('super_pdp_as_pa') else 'Désactivé'}")
        if is_auto_numbering():
            try:
                with db_cursor() as (conn, _cursor):
                    next_num = get_next_invoice_number(conn)
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
    # HTML/PDF uniquement
    'legal_form': CONFIG.get('cie_legal_form', ''),
    'iban': CONFIG.get('cie_IBAN', ''),
    # XML Factur-X (notes BR-FR-05)
    'pmt_text': CONFIG.get('pmt_text', ''),
    'pmd_text': CONFIG.get('pmd_text', ''),
}

app = Flask(__name__, template_folder='resources/templates', static_folder='resources', static_url_path='/static')
app.secret_key = 'facturx-secret-key-change-in-production'

TYPE_LABELS = {
    '380': 'Facture',
    '381': 'Avoir',
    '384': 'Facture rectificative',
    '389': 'Facture d\'acompte',
}


def validate_step1(data: dict, auto_numbering: bool = False) -> list[dict]:
    """Valide les données du formulaire step1."""
    errors = []

    if not auto_numbering and not data.get('invoice_number', '').strip():
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

        # Validation catégorie TVA pour taux 0%
        try:
            vat_rate = Decimal(str(line.get('vat_rate', 20)))
        except (ValueError, TypeError):
            vat_rate = Decimal('20')

        if vat_rate == 0:
            vat_cat = line.get('vat_category', '').strip()
            if not vat_cat:
                errors.append({
                    'field': f'lines[{i}][vat_category]',
                    'message': f'Ligne {i+1} : la catégorie TVA est obligatoire quand le taux est à 0%'
                })
            elif vat_cat in ('E', 'AE', 'G', 'K', 'O'):
                exemption_code = line.get('vat_exemption_code', '').strip()
                exemption_reason = line.get('vat_exemption_reason', '').strip()
                if not exemption_code and not exemption_reason:
                    errors.append({
                        'field': f'lines[{i}][vat_exemption_code]',
                        'message': f'Ligne {i+1} : un code VATEX ou un motif d\'exonération est requis pour la catégorie {vat_cat}'
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
            'vat_category': form_data.get(f'lines[{idx}][vat_category]', ''),
            'vat_exemption_code': form_data.get(f'lines[{idx}][vat_exemption_code]', ''),
            'vat_exemption_reason': form_data.get(f'lines[{idx}][vat_exemption_reason]', ''),
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
    """Redirige vers le dashboard si PostgreSQL activé, sinon vers step1."""
    if CONFIG.get('is_db_pg') is True:
        return redirect(url_for('dashboard'))
    return redirect(url_for('show_step1'))


@app.route('/dashboard')
def dashboard():
    """Affiche le tableau de bord facturation (requiert is_db_pg=True)."""
    if CONFIG.get('is_db_pg') is not True:
        return redirect(url_for('show_step1'))

    db_host = os.environ.get('DB_URL', 'localhost')
    db_name = os.environ.get('DB_NAME', 'k_factur_x')

    # Token OAuth2 SuperPDP
    session['OAUTH_TOKEN'] = None
    pdp_token_error = None
    pdp_token_validity = None

    if CONFIG.get('super_pdp_as_pa') is True:
        try:
            token_response = get_pdp_token()
            session['OAUTH_TOKEN'] = token_response['access_token']
            expires_in = token_response.get('expires_in', 0)
            expiry_time = datetime.now() + timedelta(seconds=int(expires_in))
            pdp_token_validity = expiry_time.strftime("%H:%M:%S")
        except (EnvironmentError, RuntimeError) as e:
            pdp_token_error = str(e)

    return render_template(
        'html/dashboard.html',
        logo_path=get_logo_url(),
        emitter=EMITTER,
        db_host=db_host,
        db_name=db_name,
        super_pdp_as_pa=CONFIG.get('super_pdp_as_pa', False),
        pdp_token_validity=pdp_token_validity,
        pdp_token_error=pdp_token_error,
    )


@app.route('/invoice/step1', methods=['GET'])
def show_step1():
    """Affiche le formulaire step1."""
    next_invoice_number = None
    client_count = 0

    auto_numbering = CONFIG.get('is_num_facturx_auto') is True
    is_db_pg = CONFIG.get('is_db_pg') is True

    if auto_numbering:
        try:
            with db_cursor() as (conn, cursor):
                next_invoice_number = get_next_invoice_number(conn)
                session['next_invoice_number'] = next_invoice_number
        except Exception as e:
            print(f"[WARNING] Impossible de calculer le prochain numéro: {e}")

    if is_db_pg:
        try:
            with db_cursor() as (_conn, cursor):
                cursor.execute("SELECT COUNT(*) FROM client_metadata")
                client_count = cursor.fetchone()[0]
        except Exception as e:
            print(f"[WARNING] Impossible de compter les clients: {e}")

    return render_template(
        'html/invoice_step1.html',
        logo_path=get_logo_url(),
        emitter=EMITTER,
        next_invoice_number=next_invoice_number,
        auto_numbering=auto_numbering,
        is_db_pg=is_db_pg,
        client_count=client_count,
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
        'recipient_legal_form': request.form.get('recipient_legal_form', ''),
        'recipient_siret': request.form.get('recipient_siret', ''),
        'recipient_vat_number': request.form.get('recipient_vat_number', ''),
        'recipient_address': request.form.get('recipient_address', ''),
        'recipient_postal_code': request.form.get('recipient_postal_code', ''),
        'recipient_city': request.form.get('recipient_city', ''),
        'recipient_country_code': request.form.get('recipient_country_code', 'FR'),
    }

    auto_num = is_auto_numbering()

    # Si numérotation auto, utiliser le numéro stocké en session (non modifiable côté client)
    if auto_num:
        stored_num = session.get('next_invoice_number')
        if stored_num:
            data['invoice_number'] = stored_num
        else:
            try:
                with db_cursor() as (conn, _cursor):
                    data['invoice_number'] = get_next_invoice_number(conn)
            except Exception as e:
                return jsonify({'success': False, 'errors': [
                    {'field': 'invoice_number', 'message': f'Erreur numérotation auto: {e}'}
                ]}), 500

    errors = validate_step1(data, auto_numbering=auto_num)

    if errors:
        return jsonify({'success': False, 'errors': errors}), 400

    # Insertion du nouveau client en base si demandé
    client_exists = False
    if CONFIG.get('is_db_pg') is True and request.form.get('save_new_client') == '1':
        try:
            with db_cursor(commit=True) as (_conn, cursor):
                cursor.execute(
                    """INSERT INTO client_metadata
                       (recipient_name, cie_legal_form, recipient_siret, recipient_vat_number,
                        recipient_address, recipient_postal_code, recipient_city, recipient_country_code)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        data['recipient_name'],
                        data['recipient_legal_form'],
                        data['recipient_siret'],
                        data['recipient_vat_number'],
                        data['recipient_address'],
                        data['recipient_postal_code'],
                        data['recipient_city'],
                        data['recipient_country_code'],
                    ),
                )
            print(f"[OK] Client {data['recipient_name']} (SIRET {data['recipient_siret']}) enregistré en base")
        except Exception as e:
            err_msg = str(e).lower()
            if 'unique' in err_msg or 'duplicate' in err_msg or 'recipient_siret' in err_msg:
                print(f"[INFO] Client SIRET {data['recipient_siret']} déjà en base, insertion ignorée")
                client_exists = True
            else:
                print(f"[WARNING] Échec de l'enregistrement du client: {e}")

    # Stocker en session
    session['invoice_data'] = data

    response = {'success': True}
    if client_exists:
        response['client_exists'] = True
    return jsonify(response)


@app.route('/api/clients/search')
def search_clients():
    """Recherche de clients par nom ou SIRET (requiert is_db_pg=True)."""
    if CONFIG.get('is_db_pg') is not True:
        return jsonify({'error': 'Base de données non activée'}), 404

    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify({'results': []})

    try:
        with db_cursor() as (_conn, cursor):
            like_pattern = f'%{q}%'
            cursor.execute(
                """SELECT id, recipient_name, cie_legal_form, recipient_siret,
                          recipient_vat_number, recipient_address, recipient_postal_code,
                          recipient_city, recipient_country_code
                   FROM client_metadata
                   WHERE recipient_name ILIKE %s OR recipient_siret ILIKE %s
                   ORDER BY recipient_name
                   LIMIT 10""",
                (like_pattern, like_pattern),
            )
            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return jsonify({'results': results})
    except Exception as e:
        print(f"[ERROR] Recherche clients: {e}")
        return jsonify({'results': [], 'error': str(e)}), 500


@app.route('/api/db/test-connection')
def test_db_connection():
    """Teste la connexion à la base de données PostgreSQL."""
    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    try:
        conn = get_db_connection()
        conn.close()
        return jsonify({
            'connected': True,
            'host': os.environ.get('DB_URL', 'localhost'),
            'database': os.environ.get('DB_NAME', 'k_factur_x'),
            'timestamp': timestamp,
        })
    except Exception as e:
        print(f"[ERROR] Test connexion BDD: {e}")
        return jsonify({
            'connected': False,
            'host': os.environ.get('DB_URL', 'localhost'),
            'database': os.environ.get('DB_NAME', 'k_factur_x'),
            'timestamp': timestamp,
        })


@app.route('/api/dashboard/stats')
def dashboard_stats():
    """Retourne les KPI du dashboard (compteurs factures)."""
    if CONFIG.get('is_db_pg') is not True:
        return jsonify({'error': 'Base de données non activée'}), 404

    stats = {'generated': 0, 'transferred': 0, 'received': 0, 'error': 0}
    try:
        with db_cursor() as (_conn, cursor):
            cursor.execute("SELECT COUNT(*) FROM sent_invoices")
            stats['generated'] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM sent_invoices WHERE status = 'SENT-OK'")
            stats['transferred'] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM sent_invoices WHERE status = 'SENT-ERROR'")
            stats['error'] = cursor.fetchone()[0]
    except Exception as e:
        print(f"[ERROR] Stats sent_invoices: {e}")

    try:
        with db_cursor() as (_conn, cursor):
            cursor.execute("SELECT COUNT(*) FROM incoming_invoices")
            stats['received'] = cursor.fetchone()[0]
    except Exception as e:
        print(f"[WARNING] Stats incoming_invoices: {e}")

    return jsonify(stats)


@app.route('/api/dashboard/invoices')
def dashboard_invoices():
    """Retourne la liste des factures pour le dashboard."""
    if CONFIG.get('is_db_pg') is not True:
        return jsonify({'error': 'Base de données non activée'}), 404

    tab = request.args.get('tab', 'sent')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    page = max(1, int(request.args.get('page', 1)))
    per_page = max(1, min(100, int(request.args.get('per_page', 5))))
    offset = (page - 1) * per_page

    has_dates = bool(date_from and date_to)

    try:
        with db_cursor() as (_conn, cursor):
            if tab == 'received':
                if has_dates:
                    cursor.execute(
                        "SELECT COUNT(*) FROM incoming_invoices WHERE invoice_date >= %s AND invoice_date <= %s",
                        (date_from, date_to),
                    )
                else:
                    cursor.execute("SELECT COUNT(*) FROM incoming_invoices")
                total = cursor.fetchone()[0]

                if has_dates:
                    cursor.execute(
                        """SELECT invoice_num, company_name, invoice_date, total_ttc
                           FROM incoming_invoices
                           WHERE invoice_date >= %s AND invoice_date <= %s
                           ORDER BY received_at DESC
                           LIMIT %s OFFSET %s""",
                        (date_from, date_to, per_page, offset),
                    )
                else:
                    cursor.execute(
                        """SELECT invoice_num, company_name, invoice_date, total_ttc
                           FROM incoming_invoices
                           ORDER BY received_at DESC
                           LIMIT %s OFFSET %s""",
                        (per_page, offset),
                    )
            else:
                if has_dates:
                    cursor.execute(
                        "SELECT COUNT(*) FROM sent_invoices WHERE invoice_date >= %s AND invoice_date <= %s",
                        (date_from, date_to),
                    )
                else:
                    cursor.execute("SELECT COUNT(*) FROM sent_invoices")
                total = cursor.fetchone()[0]

                if has_dates:
                    cursor.execute(
                        """SELECT invoice_num, company_name, invoice_date, total_ttc, status
                           FROM sent_invoices
                           WHERE invoice_date >= %s AND invoice_date <= %s
                           ORDER BY created_at DESC
                           LIMIT %s OFFSET %s""",
                        (date_from, date_to, per_page, offset),
                    )
                else:
                    cursor.execute(
                        """SELECT invoice_num, company_name, invoice_date, total_ttc, status
                           FROM sent_invoices
                           ORDER BY created_at DESC
                           LIMIT %s OFFSET %s""",
                        (per_page, offset),
                    )

            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()

            invoices = []
            for row in rows:
                inv = dict(zip(columns, row))
                # Sérialiser les types non-JSON
                if inv.get('invoice_date'):
                    inv['invoice_date'] = str(inv['invoice_date'])
                if inv.get('total_ttc') is not None:
                    inv['total_ttc'] = float(inv['total_ttc'])
                if inv.get('status') is not None:
                    inv['status'] = str(inv['status'])
                invoices.append(inv)

            total_pages = math.ceil(total / per_page) if total > 0 else 1
            return jsonify({
                'invoices': invoices,
                'total': total,
                'page': page,
                'per_page': per_page,
                'total_pages': total_pages,
            })
    except Exception as e:
        print(f"[ERROR] Dashboard invoices: {e}")
        return jsonify({'invoices': [], 'error': str(e)}), 500


@app.route('/api/clients/count')
def count_clients():
    """Retourne le nombre de clients en base (requiert is_db_pg=True)."""
    if CONFIG.get('is_db_pg') is not True:
        return jsonify({'error': 'Base de données non activée'}), 404

    try:
        with db_cursor() as (_conn, cursor):
            cursor.execute("SELECT COUNT(*) FROM client_metadata")
            count = cursor.fetchone()[0]
            return jsonify({'count': count})
    except Exception as e:
        print(f"[ERROR] Comptage clients: {e}")
        return jsonify({'count': 0, 'error': str(e)}), 500


@app.route('/invoice/step2')
def show_step2():
    """Affiche le formulaire step2 avec les données de step1."""
    invoice_data = session.get('invoice_data')

    if not invoice_data:
        return redirect(url_for('show_step1'))

    invoice = {
        **invoice_data,
        'type_label': TYPE_LABELS.get(invoice_data['type_code'], 'Facture'),
        'issue_date_display': format_date_display(invoice_data['issue_date']),
        'due_date_display': format_date_display(invoice_data['due_date']),
    }

    return render_template(
        'html/invoice_step2.html',
        logo_path=get_logo_url(),
        emitter=EMITTER,
        invoice=invoice,
    )


def _sanitize_invoice_number(invoice_number: str) -> str:
    """Nettoie le numéro de facture pour l'utiliser dans un nom de fichier."""
    return re.sub(r'[^\w\-]', '_', invoice_number)


def save_to_storage(content, invoice_number: str, storage_type: str) -> str:
    """Sauvegarde un fichier (xml ou pdf) dans le répertoire de stockage."""
    config_key = f'{storage_type}_storage'
    defaults = {'xml': './data/factures-xml', 'pdf': './data/factures-pdf'}
    storage_dir = CONFIG.get(config_key, defaults[storage_type])

    safe_number = _sanitize_invoice_number(invoice_number)
    filename = f"{safe_number}.{storage_type}"
    filepath = Path(storage_dir) / filename

    if storage_type == 'xml':
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    else:
        with open(filepath, 'wb') as f:
            f.write(content)

    print(f"[OK] {storage_type.upper()} sauvegardé: {filepath}")
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

    try:
        auto_num = is_auto_numbering()

        # Calculer les totaux avant la génération pour disposer de total_ttc
        invoice_totals = calculate_invoice_totals(lines)
        total_ttc_value = float(invoice_totals['total_ttc'])

        try:
            # Si numérotation auto : ouvrir connexion, lock table, calcul du numéro
            if auto_num:
                with db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("LOCK TABLE sent_invoices IN EXCLUSIVE MODE")
                    cursor.close()
                    invoice_data['invoice_number'] = get_next_invoice_number(conn)
                    session['invoice_data'] = invoice_data

                    # Génération dans la transaction (le lock empêche les doublons)
                    full_data = {
                        'emitter': EMITTER,
                        'invoice': invoice_data,
                        'lines': lines,
                    }
                    pdf_bytes = generate_invoice_pdf(full_data, logo_path=LOGO_PATH)
                    xml_content = generate_facturx_xml(full_data)
                    facturx_pdf_bytes = generate_from_binary(
                        pdf_file=pdf_bytes,
                        xml=xml_content.encode('utf-8'),
                        flavor='factur-x',
                        level='en16931',
                        check_xsd=True,
                        pdf_metadata={
                            'author': EMITTER['name'],
                            'title': f"Facture {invoice_data['invoice_number']}",
                            'subject': 'Facture électronique Factur-X',
                        }
                    )
                    xml_filepath = save_to_storage(xml_content, invoice_data['invoice_number'], 'xml')
                    pdf_filepath = save_to_storage(facturx_pdf_bytes, invoice_data['invoice_number'], 'pdf')

                    insert_sent_invoice(
                        conn,
                        invoice_num=invoice_data['invoice_number'],
                        company_name=invoice_data['recipient_name'],
                        company_siret=invoice_data['recipient_siret'],
                        xml_content=xml_content,
                        pdf_path=pdf_filepath,
                        invoice_date=invoice_data['issue_date'],
                        total_ttc=total_ttc_value,
                    )
                    conn.commit()
                    print(f"[OK] Facture {invoice_data['invoice_number']} insérée en base")
            else:
                # Pas de numérotation auto : génération simple
                full_data = {
                    'emitter': EMITTER,
                    'invoice': invoice_data,
                    'lines': lines,
                }
                pdf_bytes = generate_invoice_pdf(full_data, logo_path=LOGO_PATH)
                xml_content = generate_facturx_xml(full_data)
                facturx_pdf_bytes = generate_from_binary(
                    pdf_file=pdf_bytes,
                    xml=xml_content.encode('utf-8'),
                    flavor='factur-x',
                    level='en16931',
                    check_xsd=True,
                    pdf_metadata={
                        'author': EMITTER['name'],
                        'title': f"Facture {invoice_data['invoice_number']}",
                        'subject': 'Facture électronique Factur-X',
                    }
                )
                xml_filepath = save_to_storage(xml_content, invoice_data['invoice_number'], 'xml')
                pdf_filepath = save_to_storage(facturx_pdf_bytes, invoice_data['invoice_number'], 'pdf')

        except Exception as e:
            print(f"[ERROR] Échec de la génération Factur-X: {e}")
            return jsonify({
                'success': False,
                'errors': [{'field': '_form', 'message': f'Erreur lors de la génération: {str(e)}'}]
            }), 500

        # Insérer en base si is_db_pg activé (sans auto_num, l'insertion auto_num est déjà faite)
        db_status = 'non_applicable'
        if auto_num:
            db_status = 'ok'
        elif CONFIG.get('is_db_pg') is True:
            try:
                with db_cursor(commit=True) as (db_conn, _cursor):
                    insert_sent_invoice(
                        db_conn,
                        invoice_num=invoice_data['invoice_number'],
                        company_name=invoice_data['recipient_name'],
                        company_siret=invoice_data['recipient_siret'],
                        xml_content=xml_content,
                        pdf_path=pdf_filepath,
                        invoice_date=invoice_data['issue_date'],
                        total_ttc=total_ttc_value,
                    )
                print(f"[OK] Facture {invoice_data['invoice_number']} insérée en base")
                db_status = 'ok'
            except Exception as e:
                print(f"[WARNING] Échec de l'insertion en base: {e}")
                db_status = 'erreur'

        # Construire le récapitulatif en session
        def _fmt(value):
            return str(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

        safe_number = _sanitize_invoice_number(invoice_data['invoice_number'])
        pdf_filename = f"{safe_number}.pdf"
        xml_filename = f"{safe_number}.xml"

        summary_lines = []
        for line in lines:
            lt = calculate_line_totals(line)
            vat_display = str(lt['vat_rate'])
            if lt['vat_category'] != 'S':
                vat_display += f" ({lt['vat_category']})"
            summary_lines.append({
                'description': line['description'],
                'quantity': str(lt['quantity']),
                'unit_price': _fmt(lt['unit_price']),
                'vat_rate': vat_display,
                'net_ht': _fmt(lt['net_ht']),
                'discount_amount': _fmt(lt['discount_amount']),
            })

        vat_breakdown = []
        for rate_key in sorted(invoice_totals['vat_breakdown'].keys(), key=lambda k: invoice_totals['vat_breakdown'][k]['rate'], reverse=True):
            info = invoice_totals['vat_breakdown'][rate_key]
            rate_display = str(info['rate'])
            if info.get('vat_category', 'S') != 'S':
                rate_display += f" ({info['vat_category']})"
            vat_breakdown.append({
                'rate': rate_display,
                'base_ht': _fmt(info['base_ht']),
                'vat_amount': _fmt(info['vat_amount']),
            })

        session['invoice_summary'] = {
            'invoice_number': invoice_data['invoice_number'],
            'type_code': invoice_data['type_code'],
            'type_label': TYPE_LABELS.get(invoice_data['type_code'], 'Facture'),
            'currency_code': invoice_data.get('currency_code', 'EUR'),
            'issue_date': format_date_display(invoice_data['issue_date']),
            'due_date': format_date_display(invoice_data.get('due_date', '')),
            'recipient_name': invoice_data['recipient_name'],
            'recipient_siret': invoice_data['recipient_siret'],
            'emitter_name': EMITTER['name'],
            'emitter_siret': EMITTER['siret'],
            'lines': summary_lines,
            'total_ht': _fmt(invoice_totals['total_ht']),
            'total_vat': _fmt(invoice_totals['total_vat']),
            'total_ttc': _fmt(invoice_totals['total_ttc']),
            'vat_breakdown': vat_breakdown,
            'pdf_filename': pdf_filename,
            'xml_filename': xml_filename,
            'db_status': db_status,
        }

        return jsonify({'success': True, 'redirect': '/invoice/step3'})
    except Exception as e:
        print(f"[ERROR] Erreur inattendue lors de la génération: {e}")
        return jsonify({
            'success': False,
            'errors': [{'field': '_form', 'message': f'Erreur inattendue: {str(e)}'}]
        }), 500


@app.route('/invoice/step3')
def show_step3():
    """Affiche la page récapitulative après génération."""
    summary = session.get('invoice_summary')
    if not summary:
        return redirect(url_for('index'))

    return render_template(
        'html/invoice_step3.html',
        logo_path=get_logo_url(),
        emitter=EMITTER,
        summary=summary,
    )


@app.route('/invoice/download-pdf')
def download_pdf():
    """Sert le PDF Factur-X depuis le répertoire de stockage."""
    summary = session.get('invoice_summary')
    if not summary:
        return redirect(url_for('index'))

    pdf_storage = CONFIG.get('pdf_storage', './data/factures-pdf')
    filename = summary['pdf_filename']

    return send_from_directory(os.path.abspath(pdf_storage), filename, as_attachment=True)


@app.route('/invoice/new')
def new_invoice():
    """Vide la session et redirige vers step1."""
    session.clear()
    return redirect(url_for('show_step1'))


if __name__ == '__main__':
    # Valider la configuration au démarrage
    validate_startup_config()
    app.run(debug=True, port=5000)
