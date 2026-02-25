# Generate-FacturX-PY

Application Flask de facturation électronique au format **Factur-X** (PDF/A-3B + XML CII embarqué).

**Profil :** EN16931 — `urn:cen.eu:en16931:2017` (Factur-X 1.07, CII D22B)

## Fonctionnalités

- **Génération PDF Factur-X** validée XSD, Schematron et PDF/A-3B (VeraPDF)
- **Interface web** en 3 étapes : infos facture/client, lignes de facturation (TVA 0–20%, rabais, catégories d'exonération), récapitulatif + téléchargement
- **Dashboard** avec KPI, tableau paginé des factures envoyées/reçues, filtres par date
- **Numérotation automatique** (`FAC-YYYY-MM-NNNN`) avec verrouillage transactionnel
- **Envoi vers plateforme agréée** (SuperPDP) avec suivi du statut et **vérification de validation** PA
- **Gestion clients** : recherche, sauvegarde, autocomplétion SIRET

## Installation

```bash
git clone <url-du-repo> && cd Generate-FacturX-PY
uv sync                       # Installer les dépendances
```

Avant de lancer le serveur, configurer l'émetteur et le `.env` (voir sections ci-dessous), puis :

```bash
uv run python app.py           # Lancer (http://localhost:5000)
```

## Configuration

### Émetteur (`resources/config/ma-conf.txt`)

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
xml_storage=./data/factures-xml
pdf_storage=./data/factures-pdf

# Notes obligatoires BR-FR-05
pmt_text=En cas de retard de paiement, une indemnité forfaitaire...
pmd_text=En cas de retard de paiement, des pénalités de retard...

# Options
is_db_pg=False
is_num_facturx_auto=False
super_pdp_as_pa=False
```

L'application valide automatiquement les formats (SIRET/SIREN/BIC/TVA, cohérence SIREN-SIRET, IBAN, textes BR-FR-05) et refuse de démarrer en cas d'erreur.

### PostgreSQL (optionnel)

Activer `is_db_pg=True` puis créer `.env` ou `.env.local` :

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=factur_x
DB_USER=postgres
DB_PASSWORD=votre_mot_de_passe
```

Scripts SQL dans `resources/sql/` :

```bash
createdb factur_x
psql -d factur_x -f resources/sql/create_table_sent_invoices.sql
psql -d factur_x -f resources/sql/create_table_client_metadata.sql
```

### SuperPDP (optionnel)

Activer `super_pdp_as_pa=True` et ajouter dans `.env` :

```env
PDP_SENDER_ID=votre_client_id
PDP_SENDER_SECRET=votre_client_secret
```

Fonctionnalités :

- Authentification OAuth2 avec cache de jeton
- Envoi groupé des factures PENDING vers la PA
- Vérification automatique de la validation PA (colonne "Validation" dans le dashboard)
- Journalisation dans `log/sent_invoices.log`

## Routes

| Méthode | Route | Description |
| ------- | ----- | ----------- |
| GET | `/` | Redirige vers dashboard ou step 1 |
| GET | `/dashboard` | Tableau de bord (KPI, factures, actions) |
| GET/POST | `/invoice/step1` | Infos facture + client |
| GET | `/invoice/step2` | Lignes de facturation |
| POST | `/invoice` | Génération PDF/XML Factur-X |
| GET | `/invoice/step3` | Récapitulatif |
| GET | `/invoice/download-pdf` | Téléchargement du PDF |
| GET | `/send-to-pa` | Envoi groupé vers PA |
| POST | `/api/send-to-pa` | API envoi PA |
| POST | `/api/dashboard/check-validations` | Vérification validation PA |
| GET | `/api/dashboard/stats` | KPI dashboard |
| GET | `/api/dashboard/invoices` | Liste factures paginée |
| GET | `/api/clients/search` | Recherche clients |

## Structure

```text
├── app.py                        # Routes Flask, validation, session
├── utils/
│   ├── facturx_generator.py      # XML Factur-X (CII, namespaces rsm/ram/udt)
│   ├── pdf_generator.py          # PDF ReportLab + OutputIntent ICC
│   ├── invoice_calc.py           # Calculs partagés (totaux, TVA)
│   ├── db.py                     # Context managers PostgreSQL
│   └── super_pdp.py              # Client API SuperPDP (OAuth2, envoi, validation)
├── tests/
│   ├── test_facturx.py           # Génération Factur-X
│   ├── test_tva0.py              # TVA 0% et exonérations
│   ├── test_token.py             # Authentification SuperPDP
│   ├── test_get_invoice_events.py # Événements facture PA
│   ├── test_send_factx2pdp.py    # Envoi facture PA
│   └── test_step1_client_save.py # Sauvegarde client
├── resources/
│   ├── config/ma-conf.txt        # Configuration émetteur
│   ├── fonts/                    # Polices Liberation Sans (PDF/A-3)
│   ├── logos/                    # Logos entreprise
│   ├── profiles/sRGB.icc         # Profil ICC PDF/A-3
│   ├── sql/                      # Scripts SQL
│   └── templates/                # Templates Jinja2
└── pyproject.toml
```

## Conformité

| Standard | Détail |
| -------- | ------ |
| EN 16931 | Profil EN16931 (Factur-X 1.07, CII D22B) |
| XSD | Validation automatique à la génération |
| Schematron | PEPPOL-EN16931, catégories TVA (S/Z/E/AE/G/K/O) avec BT-120/BT-121 |
| PDF/A-3B | Polices embarquées, profil ICC sRGB, validé VeraPDF |

## Licence

Projet privé SNTPK.

---

**Version :** 1.4.0 | **Python :** 3.12+ | **Dernière mise à jour :** 2026-02-25
