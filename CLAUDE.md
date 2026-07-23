# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commandes

```bash
# Installation des dépendances
uv sync

# Lancement de l'application (port 5000)
uv run python app.py

# Ajouter une dépendance
uv add <package>

# Pour PostgreSQL (si is_db_pg=True)
uv add psycopg2-binary
```

## Architecture

Application Flask générant des factures électroniques au format Factur-X
(norme EN 16931), avec envoi et réception via la Plateforme Agréée
SUPER PDP.

### Flux de données

1. **Configuration** (`resources/config/*.conf`) → Config de base
   `burgerQueen.conf` chargée au démarrage et validée par
   `validate_startup_config()` ; chaque fichier `.conf` avec un `name`
   non vide devient un émetteur sélectionnable (`discover_emitters()`)
2. **Step 1** (`/`) → Formulaire infos facture + client → Stocké en
   `session['invoice_data']`
3. **Step 2** (`/invoice/step2`) → Lignes de facturation avec calculs TVA
4. **Génération** (`POST /invoice`) → `generate_facturx_xml()` +
   `generate_invoice_pdf()` → PDF/A-3 Factur-X, XML dans `xml_storage`,
   PDF dans `pdf_storage`, ligne dans la table `sent_invoices`
5. **Envoi PA** (`/send-to-pa`, `POST /api/send-to-pa`) → téléversement
   du PDF Factur-X vers SUPER PDP, suivi des statuts via
   `POST /api/dashboard/check-validations`
6. **Réception** (`POST /api/dashboard/fetch-invoices`) → liste les
   factures `direction=in` chez SUPER PDP, télécharge PDF + XML dans
   `incoming_storage`, insère dans la table `incoming_invoices`

### Modules principaux

- **app.py** : Routes Flask, validation config au démarrage, gestion
  session (émetteur courant), validation formulaires
- **utils/** : Package regroupant les modules utilitaires
  - **utils/facturx_generator.py** : Génération XML CrossIndustryInvoice
    (CII) avec namespaces `rsm`, `ram`, `udt`
  - **utils/pdf_generator.py** : Génération PDF de facture avec ReportLab
  - **utils/invoice_calc.py** : Calculs partagés (totaux lignes, totaux
    facture, TVA)
  - **utils/db.py** : Connexion et context managers PostgreSQL
  - **utils/super_pdp.py** : Client API SUPER PDP (OAuth2, envoi,
    statuts, réception) — HTTP via `curl`/`subprocess`

### Configuration (`resources/config/*.conf`)

Format clé=valeur. La config de base est `burgerQueen.conf` (réglages
globaux + identité) ; les autres fichiers ne portent que l'identité d'un
émetteur. Champs validés au démarrage :

- `siret` (14 chiffres), `siren` (9 chiffres), `bic`, `num_tva`, `name`,
  `address`, `cie_legal_form`, `cie_IBAN`, `pmt_text`, `pmd_text`
- `recipient_pepol` : identifiant Peppol de l'émetteur (9 à 32
  caractères, chiffres ou `_`)
- `pdp_env_suffix` : suffixe des identifiants OAuth SUPER PDP dans
  `.env.local` (ex. `BURGERQ` → `PDP_SENDER_ID_BURGERQ`)
- `logo` : Fallback sur `./resources/logos/underwork.jpeg` si
  absent/invalide
- `is_db_pg` : Si `True`, requiert `.env` ou `.env.local` avec
  credentials PostgreSQL
- `xml_storage`, `pdf_storage`, `incoming_storage` : Répertoires créés
  automatiquement

### Templates Jinja2 (`resources/templates/html/`)

- `invoice_step1.html` : Formulaire initial (POST vers `/invoice/step1`)
- `invoice_step2.html` : Lignes + totaux (POST vers `/invoice`)
- `invoice_step3.html` : Récapitulatif après génération
- `dashboard.html` : KPI, listes envoyées/reçues, actions PA
- `send_to_pa.html` : Envoi groupé des factures PENDING

## Markdown (markdownlint)

Lors de l'édition de fichiers `.md`, respecter ces règles :

- **MD060** : Espaces autour des pipes dans les séparateurs de tableaux
  (`| --- | --- |` et non `|---|---|`)
- **MD032** : Ligne vide avant et après chaque liste à puces ou numérotée
- **MD040** : Toujours spécifier un langage sur les blocs de code
  (` ```bash `, ` ```text `, ` ```python `, etc.)

## Versioning

Lors d'un changement de version, toujours mettre à jour **les deux
fichiers** :

- `pyproject.toml` → champ `version`
- `README.md` → ligne `**Version :**` en bas du fichier

## Factur-X

Profil généré : **EN 16931** — guideline
`urn:cen.eu:en16931:2017` (BT-24) et `level='en16931'` pour la lib
`factur-x` (PDF/A-3). Le profil BASIC n'est plus utilisé.

Structure XML générée :

- `ExchangedDocumentContext` → `BusinessProcessSpecifiedDocumentContextParameter`
  (BT-23, obligatoire BR-FR-08, défaut `B1` = dépôt facture B2B) +
  `GuidelineSpecifiedDocumentContextParameter`
- `ExchangedDocument` → ID, TypeCode, IssueDateTime
- `SupplyChainTradeTransaction` → Lignes, parties (Seller/Buyer, SIREN
  schemeID `0002`, endpoint Peppol schemeID `0225`), TVA, totaux

## SUPER PDP

- API : `https://api.superpdp.tech` (préfixe `/v1.beta`), spec OpenAPI :
  `https://api.superpdp.tech/openapi/superpdp.json`, doc :
  `https://www.superpdp.tech/documentation/`
- Auth OAuth2 `client_credentials` (`POST /oauth2/token`) ; un token est
  scopé à UNE société — les identifiants sont donc **par émetteur**
  (`PDP_SENDER_ID_<pdp_env_suffix>` dans `.env.local`), token mis en
  cache dans `.pdp_token_cache-<suffixe>.json`
- Envoi : `POST /v1.beta/invoices` (body = PDF Factur-X) ; statuts :
  `GET /v1.beta/invoices/{id}` (événements `api:uploaded`, `fr:2xx`,
  `fr:213` = rejetée, `api:validated`)
- Réception : `GET /v1.beta/invoices?direction=in` (pagination `limit` +
  `starting_after_id`/`has_after`) ; téléchargement :
  `GET /v1.beta/invoices/{id}?format=factur-x|cii|ubl|en16931|original`
- Les échanges PA sont journalisés dans `log/sent_invoices.log`
