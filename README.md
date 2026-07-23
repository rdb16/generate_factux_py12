# Generate-FacturX-PY

Application Flask de facturation électronique au format **Factur-X** (PDF/A-3B + XML CII embarqué), avec envoi et réception via la Plateforme Agréée **SUPER PDP**.

**Profil :** EN16931 — `urn:cen.eu:en16931:2017` (Factur-X 1.07, CII D22B)

## Fonctionnalités

- **Génération PDF Factur-X** validée XSD, Schematron et PDF/A-3B (VeraPDF)
- **Factures et avoirs** : type de document 380 (facture), 381 (avoir), 384 (rectificative), 389 (acompte) ; un avoir (montants positifs, EN 16931) référence obligatoirement la facture d'origine (BT-25/BT-26)
- **Interface web** en 3 étapes : infos facture/client, lignes de facturation (TVA 0–20%, rabais, catégories d'exonération), récapitulatif + téléchargement
- **Multi-émetteurs** : un fichier de config `.conf` par société, sélection de l'émetteur courant depuis le dashboard
- **Dashboard** avec KPI, tableau paginé des factures envoyées/reçues, filtres par date
- **Numérotation automatique** (`FAC-YYYY-MM-NNNN`, séquence remise à zéro chaque mois) avec verrouillage transactionnel
- **Envoi vers plateforme agréée** (SUPER PDP) avec suivi du statut et **vérification de validation** PA
- **Réception des factures** reçues depuis SUPER PDP (téléchargement PDF/XML, insertion en base, consultation du PDF au clic)
- **Gestion clients** : recherche, sauvegarde, autocomplétion SIRET

## Installation

```bash
git clone <url-du-repo> && cd Generate-FacturX-PY
uv sync                       # Installer les dépendances
```

Avant de lancer le serveur, configurer l'émetteur et le `.env.local` (voir sections ci-dessous), puis :

```bash
uv run python app.py           # Lancer (http://localhost:5000)
```

## Configuration

### Émetteur (`resources/config/*.conf`)

La config de base est `burgerQueen.conf` : elle porte l'identité d'un émetteur **et** les réglages globaux (base de données, SUPER PDP, numérotation, stockage). Chaque autre fichier `.conf` avec un `name` non vide devient un émetteur sélectionnable (identité seule ; les réglages globaux viennent de la config de base).

```ini
name=Votre Entreprise SARL
address=123 rue de la Paix
postal_code=75001
city=Paris
country_code=FR
siren=123456789
siret=12345678901234
num_tva=FR12345678901
bic=BNPAFRPPXXX
cie_legal_form=S.A.R.L
cie_IBAN=FR7612345678901234567890123
logo=./resources/logos/mon-logo.png

# Identifiant Peppol de l'émetteur (9 à 32 caractères : chiffres ou _)
recipient_pepol=12345678901234

# Suffixe des identifiants OAuth SUPER PDP dans .env.local
pdp_env_suffix=MONENTREPRISE

# Notes obligatoires BR-FR-05
pmt_text=En cas de retard de paiement, une indemnité forfaitaire...
pmd_text=En cas de retard de paiement, des pénalités de retard...

# Réglages globaux (config de base uniquement)
xml_storage=./data/factures-xml
pdf_storage=./data/factures-pdf
incoming_storage=./data/incoming-invoices
is_db_pg=False
is_num_facturx_auto=False
super_pdp_as_pa=False
```

L'application valide automatiquement les formats (SIRET/SIREN/BIC/TVA, cohérence SIREN-SIRET, IBAN, identifiant Peppol, textes BR-FR-05) et refuse de démarrer en cas d'erreur.

### PostgreSQL (optionnel)

Activer `is_db_pg=True` puis créer `.env` ou `.env.local` :

```env
DB_URL=localhost
DB_PORT=5432
DB_NAME=k_factur_x
DB_USER=postgres
DB_PASS=votre_mot_de_passe

# Clé de signature des sessions Flask
# (python -c "import secrets; print(secrets.token_hex(32))")
FLASK_SECRET_KEY=...
```

Scripts SQL dans `resources/sql/` :

```bash
createdb k_factur_x
psql -d k_factur_x -f resources/sql/create_table_sent_invoices.sql
psql -d k_factur_x -f resources/sql/create_table_client_metadata.sql
psql -d k_factur_x -f resources/sql/create_table_incoming_invoices.sql
```

### SUPER PDP (optionnel)

Activer `super_pdp_as_pa=True`. Un jeton OAuth étant scopé à **une** société, les identifiants sont définis **par émetteur** dans `.env.local`, avec le suffixe déclaré par `pdp_env_suffix` :

```env
PDP_SENDER_ID_MONENTREPRISE=votre_client_id
PDP_SENDER_SECRET_MONENTREPRISE=votre_client_secret
```

Les identifiants OAuth se créent dans l'application SUPER PDP (menu **Applications** → *Nouvelle application* de type *confidentielle*).

Fonctionnalités :

- Authentification OAuth2 avec cache de jeton par émetteur (`.pdp_token_cache-<suffixe>.json`)
- Envoi groupé des factures PENDING vers la PA
- Vérification automatique de la validation PA (colonne « Validation » du dashboard)
- Réception des factures adressées à l'émetteur (`direction=in`)
- Journalisation dans `log/sent_invoices.log`

Référence API : `https://api.superpdp.tech` (préfixe `/v1.beta`), spec OpenAPI `https://api.superpdp.tech/openapi/superpdp.json`.

## Routes

| Méthode | Route | Description |
| ------- | ----- | ----------- |
| GET | `/` | Redirige vers dashboard ou step 1 |
| GET | `/dashboard` | Tableau de bord (KPI, factures, actions) |
| POST | `/api/emitter/select` | Sélection de l'émetteur courant |
| GET/POST | `/invoice/step1` | Infos facture/avoir + client |
| GET | `/invoice/step2` | Lignes de facturation |
| POST | `/invoice` | Génération PDF/XML Factur-X |
| GET | `/invoice/step3` | Récapitulatif |
| GET | `/invoice/download-pdf` | Téléchargement du PDF généré |
| GET | `/invoice/incoming-pdf/<num>` | PDF d'une facture reçue |
| GET | `/invoice/new` | Nouvelle facture (conserve l'émetteur) |
| GET | `/send-to-pa` | Envoi groupé vers PA |
| POST | `/api/send-to-pa` | API envoi PA |
| POST | `/api/dashboard/fetch-invoices` | Récupération des factures reçues |
| POST | `/api/dashboard/check-validations` | Vérification validation PA |
| GET | `/api/dashboard/stats` | KPI dashboard |
| GET | `/api/dashboard/invoices` | Liste factures paginée (envoyées/reçues) |
| GET | `/api/clients/search` | Recherche clients |
| GET | `/api/clients/count` | Nombre de clients en base |

## Structure

```text
├── app.py                        # Routes Flask, validation, session, émetteurs
├── utils/
│   ├── facturx_generator.py      # XML Factur-X (CII, namespaces rsm/ram/udt/qdt)
│   ├── pdf_generator.py          # PDF ReportLab + OutputIntent ICC
│   ├── invoice_calc.py           # Calculs partagés (totaux, TVA)
│   ├── db.py                     # Context managers PostgreSQL
│   └── super_pdp.py              # Client API SUPER PDP (OAuth2, envoi, statuts, réception)
├── resources/
│   ├── config/*.conf             # Configuration émetteurs (burgerQueen.conf = base)
│   ├── fonts/                    # Polices Liberation Sans (PDF/A-3)
│   ├── logos/                    # Logos entreprise
│   ├── profiles/sRGB.icc         # Profil ICC PDF/A-3
│   ├── sql/                      # Scripts SQL (sent/incoming invoices, clients)
│   └── templates/html/           # Templates Jinja2
├── data/                         # Factures générées et reçues (non versionné)
└── pyproject.toml
```

## Conformité

| Standard | Détail |
| -------- | ------ |
| EN 16931 | Profil EN16931 (Factur-X 1.07, CII D22B) |
| XSD | Validation automatique à la génération |
| Schematron | PEPPOL-EN16931, catégories TVA (S/Z/E/AE/G/K/O) avec BT-120/BT-121 |
| BR-FR | Notes BR-FR-05, mode de facturation BT-23 (BR-FR-08), avoir avec facture d'origine (BR-FR-04) |
| PDF/A-3B | Polices embarquées, profil ICC sRGB, validé VeraPDF |

## Licence

Projet privé SNTPK.

---

**Version :** 1.6.0 | **Python :** 3.12+ | **Dernière mise à jour :** 2026-07-23
