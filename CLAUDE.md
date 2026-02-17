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

Application Flask générant des factures électroniques au format Factur-X (norme EN 16931).

### Flux de données

1. **Configuration** (`resources/config/ma-conf.txt`) → Chargée au démarrage, validée par `validate_startup_config()`
2. **Step 1** (`/`) → Formulaire infos facture + client → Stocké en `session['invoice_data']`
3. **Step 2** (`/invoice/step2`) → Lignes de facturation avec calculs TVA
4. **Génération** (`POST /invoice`) → `facturx_generator.generate_facturx_xml()` → XML sauvegardé dans `xml_storage`

### Modules principaux

- **app.py** : Routes Flask, validation config au démarrage, gestion session, validation formulaires
- **facturx_generator.py** : Génération XML CrossIndustryInvoice (CII) avec namespaces `rsm`, `ram`, `udt`

### Configuration (`resources/config/ma-conf.txt`)

Format clé=valeur. Champs émetteur validés au démarrage :
- `siret` (14 chiffres), `siren` (9 chiffres), `bic`, `num_tva`, `name`, `address`
- `logo` : Fallback sur `./resources/logos/underwork.jpeg` si absent/invalide
- `is_db_pg` : Si `True`, requiert `.env` ou `.env.local` avec credentials PostgreSQL
- `xml_storage`, `pdf_storage` : Répertoires créés automatiquement

### Templates Jinja2

- `resources/templates/invoice_step1.html` : Formulaire initial (POST vers `/invoice/step1`)
- `resources/templates/invoice_step2.html` : Lignes + totaux (POST vers `/invoice`)

## Versioning

Lors d'un changement de version, toujours mettre à jour **les deux fichiers** :
- `pyproject.toml` → champ `version`
- `README.md` → ligne `**Version :**` en bas du fichier

## Factur-X

Profil : `urn:factur-x.eu:1p0:basic`

Structure XML générée :
- `ExchangedDocumentContext` → Guidelines
- `ExchangedDocument` → ID, TypeCode, IssueDateTime
- `SupplyChainTradeTransaction` → Lignes, parties (Seller/Buyer), TVA, totaux
