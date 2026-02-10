# Generate-FacturX-PY

Application Flask pour générer des factures électroniques au format Factur-X (norme EN 16931).

## Description

Crée des **PDF Factur-X conformes** : PDF visuel (ReportLab) + XML embarqué (CII), validés XSD, Schematron et PDF/A-3B (VeraPDF).

**Profil :** EN16931 — `urn:cen.eu:en16931:2017` (Factur-X 1.07, CII D22B)

### Interface web en trois étapes

1. **Informations générales** — Numéro de facture (manuel ou auto), type, devise, dates, client (raison sociale, SIRET, TVA intracom, adresse), références
2. **Lignes de facturation** — Description, quantité, prix unitaire HT, taux TVA (0–20%), rabais optionnels, calcul automatique des totaux et récap TVA par catégorie. Pour TVA 0% : sélection de la catégorie (Z/E/AE/G/K/O) et motif d'exonération (BT-120/BT-121)
3. **Récapitulatif** — Résumé complet, ventilation TVA, téléchargement du PDF Factur-X, nouvelle facture

## Installation et commandes

```bash
git clone <url-du-repo> && cd Generate-FacturX-PY
uv sync                          # Installer les dépendances
uv run python app.py             # Lancer l'application (http://localhost:5000)
uv run python test_facturx.py    # Tester la génération Factur-X
uv add <package>                 # Ajouter une dépendance
```

### Dépendances principales

```toml
dependencies = [
    "flask>=3.1.0",           # Framework web
    "jinja2>=3.1.6",          # Templates HTML
    "factur-x>=3.15",         # Génération PDF Factur-X (inclut pypdf)
    "reportlab>=4.4.9",       # Génération PDF
    "psycopg2-binary>=2.9.11",# Driver PostgreSQL (optionnel)
]
```

## Configuration

Créer `resources/config/ma-conf.txt` :

```ini
# Émetteur
name=Votre Entreprise SARL
address=123 rue de la Paix
postal_code=75001
city=Paris
country_code=FR
siren=123456789
siret=12345678901234
num_tva=FR12345678901
bic=BNPAFRPPXXX

# Logo (optionnel, fallback sur underwork.jpeg)
logo=./resources/logos/mon-logo.png

# Stockage (répertoires créés automatiquement)
xml_storage=./data/factures-xml
pdf_storage=./data/factures-pdf

# Base de données PostgreSQL (optionnel)
is_db_pg=False

# Numérotation auto des factures (requiert is_db_pg=True)
is_num_facturx_auto=False

# Informations complémentaires émetteur
cie_legal_form=S.A.R.L
cie_IBAN=FR7612345678901234567890123

# Notes obligatoires Factur-X BR-FR-05
pmt_text=En cas de retard de paiement, une indemnité forfaitaire pour frais de recouvrement de 40€ sera exigée (Art. L441-10 et D441-5 du Code de commerce).
pmd_text=En cas de retard de paiement, des pénalités de retard seront appliquées au taux de 3 fois le taux d'intérêt légal en vigueur (Art. L441-10 du Code de commerce).
```

### Validation au démarrage

L'application valide automatiquement : formats SIRET/SIREN/BIC/TVA, cohérence SIREN-SIRET, forme juridique, IBAN, textes BR-FR-05, et crée les répertoires de stockage. En cas d'erreur, elle refuse de démarrer.

## Routes Flask

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/` | Formulaire step 1 (infos facture + client) |
| POST | `/invoice/step1` | Valide step 1, stocke en session (JSON) |
| GET | `/invoice/step2` | Formulaire step 2 (lignes de facturation) |
| POST | `/invoice` | Valide step 2, génère PDF/XML, redirige vers step 3 |
| GET | `/invoice/step3` | Récapitulatif de la facture générée |
| GET | `/invoice/download-pdf` | Télécharge le PDF Factur-X |
| GET | `/invoice/new` | Vide la session, retour step 1 |

## TVA 0% : catégories et motifs d'exonération

Quand le taux TVA > 0%, la catégorie `S` (standard) est appliquée automatiquement. Quand le taux est à 0%, l'utilisateur choisit parmi :

| Code | Catégorie | Motif requis | Cas d'usage |
|------|-----------|--------------|-------------|
| `Z` | Taux zéro | Non | Taux zéro réglementaire |
| `E` | Exonéré | Oui | Franchise en base, soins médicaux, enseignement |
| `AE` | Autoliquidation | Oui | Sous-traitance BTP, art. 283-2 CGI |
| `G` | Export hors UE | Oui | Livraisons extracommunautaires |
| `K` | Intracommunautaire | Oui | Livraisons B2B au sein de l'UE |
| `O` | Hors champ TVA | Oui | Opérations hors champ territorial |

Pour les catégories E, AE, G, K et O, un **code VATEX** (BT-121) doit être renseigné, filtré par catégorie :

- **E** : `VATEX-EU-132`, `VATEX-FR-FRANCHISE`, `VATEX-FR-CNWVAT`, etc.
- **AE** : `VATEX-EU-AE`, `VATEX-FR-AE`
- **G** : `VATEX-EU-G`, `VATEX-FR-CGI275`
- **K** : `VATEX-EU-IC`
- **O** : `VATEX-EU-O`

Le XML généré inclut `ExemptionReason` (BT-120) et `ExemptionReasonCode` (BT-121), requis par les règles Schematron BR-E-10, BR-AE-10, BR-G-10, BR-K-10 et BR-O-10 :

```xml
<ram:ApplicableTradeTax>
  <ram:CalculatedAmount>0.00</ram:CalculatedAmount>
  <ram:TypeCode>VAT</ram:TypeCode>
  <ram:ExemptionReason>Franchise en base de TVA</ram:ExemptionReason>
  <ram:ExemptionReasonCode>VATEX-FR-FRANCHISE</ram:ExemptionReasonCode>
  <ram:BasisAmount>1000.00</ram:BasisAmount>
  <ram:CategoryCode>E</ram:CategoryCode>
  <ram:RateApplicablePercent>0.00</ram:RateApplicablePercent>
</ram:ApplicableTradeTax>
```

## Base de données PostgreSQL (optionnel)

Si `is_db_pg=True`, créer `.env` ou `.env.local` :

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=facturx
DB_USER=postgres
DB_PASSWORD=votre_mot_de_passe
```

### Numérotation automatique

Lorsque `is_num_facturx_auto=True` et `is_db_pg=True`, le numéro de facture est généré au format `FAC-YYYY-MM-NNNN` (ex: `FAC-2026-02-0001`).

Un **verrouillage transactionnel** garantit l'unicité en accès concurrent : lock pendant la génération (XML + PDF + insertion), relâché au commit/rollback.

## Structure du projet

```
Generate-FacturX-PY/
├── app.py                        # Application Flask (routes, validation, session)
├── facturx_generator.py          # Générateur XML Factur-X (profil EN16931)
├── pdf_generator.py              # Générateur PDF ReportLab + OutputIntent ICC
├── test_facturx.py               # Script de test de génération
├── pyproject.toml                # Configuration uv et dépendances
├── resources/
│   ├── config/ma-conf.txt        # Configuration émetteur
│   ├── fonts/                    # Polices Liberation Sans (PDF/A-3)
│   ├── logos/                    # Logos entreprise
│   ├── profiles/sRGB.icc        # Profil ICC pour OutputIntent PDF/A-3
│   ├── sql/                      # Scripts SQL (si PostgreSQL activé)
│   └── templates/                # Templates HTML Jinja2 + XMP
└── data/                         # Fichiers générés (gitignored)
```

## Conformité

| Standard | Détail |
|----------|--------|
| **EN 16931** | Profil EN16931 (Factur-X 1.07, CII D22B) |
| **XSD** | Validation automatique à la génération |
| **Schematron** | PEPPOL-EN16931, catégories TVA (S/Z/E/AE/G/K/O) avec BT-120/BT-121 |
| **PDF/A-3B** | Polices Liberation Sans embarquées, profil ICC sRGB, validé VeraPDF |

## Ressources

- [Factur-X Official](https://fnfe-mpe.org/factur-x/)
- [Norme EN 16931](https://ec.europa.eu/digital-building-blocks/sites/display/DIGITAL/Compliance+with+eInvoicing+standard)
- [factur-x Python Library](https://github.com/akretion/factur-x)
- [ReportLab Documentation](https://www.reportlab.com/docs/reportlab-userguide.pdf)

## Licence

Projet privé SNTPK.

---

**Version :** 1.1.0 | **Python :** 3.12+ | **Dernière mise à jour :** 2026-02-10
