# Generate-FacturX-PY

Application Flask pour générer des factures électroniques au format Factur-X (norme EN 16931).

## Description

Ce projet permet de créer des **factures électroniques conformes** au standard Factur-X, le format hybride franco-allemand basé sur PDF/A-3 avec XML embarqué.

Le système génère des **PDF Factur-X complets** :
- PDF de facture visuel (généré avec ReportLab)
- XML structuré conforme EN 16931 (profil EN16931)
- Validation XSD officielle et conformité Schematron
- PDF/A-3B validé VeraPDF (polices embarquées + profil ICC sRGB)

### Interface web en trois étapes

1. **Étape 1 - Informations générales**
   - Numéro de facture (manuel ou auto), type de document, devise
   - Dates d'émission et d'échéance
   - Informations client : raison sociale, SIRET, TVA intracommunautaire
   - Adresse complète : rue, code postal, ville, pays
   - Références : bon de commande, référence acheteur

2. **Étape 2 - Lignes de facturation**
   - Description produit/service
   - Quantité, prix unitaire HT
   - Taux de TVA (0%, 5.5%, 10%, 20%)
   - Rabais optionnels (pourcentage ou montant fixe)
   - Calcul automatique des totaux HT, TVA, TTC
   - Récapitulatif par taux de TVA

3. **Étape 3 - Récapitulatif**
   - Résumé complet : facture, émetteur, client
   - Tableau des lignes de facturation (lecture seule)
   - Ventilation TVA par taux et totaux (HT, TVA, TTC)
   - Opérations effectuées : fichiers PDF/XML générés, statut base de données
   - Téléchargement du PDF Factur-X
   - Bouton « Nouvelle facture » (vide la session)



## Installation

```bash
# Cloner le projet
git clone <url-du-repo>
cd Generate-FacturX-PY

# Installer les dépendances
uv sync
```

### Dépendances principales

```toml
dependencies = [
    "flask>=3.1.0",           # Framework web
    "jinja2>=3.1.6",          # Templates HTML
    "factur-x>=3.15",         # Génération PDF Factur-X (inclut pypdf)
    "reportlab>=4.4.9",       # Génération PDF
    "psycopg2-binary>=2.9.11",# Driver PostgreSQL
]
# pypdf (dépendance transitive de factur-x) est utilisé
# pour injecter le profil ICC sRGB (OutputIntent PDF/A-3)
```

## Configuration

### 1. Fichier de configuration émetteur

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

# Logo (optionnel)
logo=./resources/logos/mon-logo.png

# Stockage
xml_storage=./data/factures-xml
pdf_storage=./data/factures-pdf

# Base de données PostgreSQL (optionnel, requiert psycopg2-binary)
is_db_pg=False

# Numérotation automatique des factures (requiert is_db_pg=True)
is_num_facturx_auto=False

# Informations complémentaires émetteur (obligatoire, HTML/PDF)
cie_legal_form=S.A.R.L
cie_IBAN=FR7612345678901234567890123

# Notes obligatoires Factur-X BR-FR-05 (obligatoire, XML/HTML/PDF)
pmt_text=En cas de retard de paiement, une indemnité forfaitaire pour frais de recouvrement de 40€ sera exigée (Art. L441-10 et D441-5 du Code de commerce).
pmd_text=En cas de retard de paiement, des pénalités de retard seront appliquées au taux de 3 fois le taux d'intérêt légal en vigueur (Art. L441-10 du Code de commerce).
```

### 2. Validation au démarrage

L'application valide automatiquement au démarrage :
- ✅ Format SIRET (14 chiffres)
- ✅ Format SIREN (9 chiffres)
- ✅ Cohérence SIREN/SIRET
- ✅ Format BIC (8 ou 11 caractères)
- ✅ Format TVA intracommunautaire
- ✅ Forme juridique (`cie_legal_form`)
- ✅ IBAN émetteur (`cie_IBAN`)
- ✅ Texte frais de recouvrement (`pmt_text`, BR-FR-05)
- ✅ Texte pénalités de retard (`pmd_text`, BR-FR-05)
- ✅ Création des répertoires de stockage

En cas d'erreur, l'application refuse de démarrer et affiche les corrections à apporter.

## Lancement

```bash
# Démarrer l'application Flask
uv run python app.py
```

L'application sera accessible sur `http://localhost:5000`

```
==============================================================
Validation de la configuration...
==============================================================

[OK] Configuration validée avec succès
  - Émetteur: Votre Entreprise SARL
  - SIRET: 12345678901234
  - Logo: ./resources/logos/mon-logo.png
  - PostgreSQL: Désactivé
  - Stockage XML: ./data/factures-xml
==============================================================
```

## Tests

### Test de génération Factur-X

```bash
uv run python test_facturx.py
```

**Résultats attendus :**
```
[1/4] Génération du PDF de base avec ReportLab...
✓ PDF généré: ~54 000 bytes (polices Liberation Sans embarquées + ICC)

[2/4] Génération du XML Factur-X...
✓ XML généré: ~6 600 caractères

[3/4] Combinaison PDF + XML avec factur-x...
✓ PDF Factur-X généré: ~108 000 bytes

[4/4] Sauvegarde...
✓ PDF sauvegardé: donné par la fichier de conf, par ex: data/test/test-facturx.pdf
✓ XML sauvegardé: donné par la fichier de conf, par ex: data/test/test-facturx.xml

[INFO] factur-x XML file successfully validated against XSD
```

### Validation PDF/A-3 avec VeraPDF
si verapdf est installé en local
```bash
verapdf --flavour 3b data/test/test-facturx.pdf
```

**Résultat attendu :**
```xml
<validationReport isCompliant="true">
  <details passedRules="146" failedRules="0" passedChecks="2310" failedChecks="0"/>
</validationReport>
```

## Structure du projet

```
Generate-FacturX-PY/
├── app.py                        # Application Flask (routes, validation, session)
├── facturx_generator.py          # Générateur XML Factur-X (profil EN16931)
├── pdf_generator.py              # Générateur PDF ReportLab + OutputIntent ICC
├── main.py                       # Point d'entrée alternatif
├── test_facturx.py               # Script de test de génération
├── pyproject.toml                # Configuration uv et dépendances
├── uv.lock                       # Verrouillage des versions
├── .python-version               # Version Python (3.12)
├── .gitignore
├── .env.template                 # Modèle de variables d'environnement
├──                     
├── README.md
├── data/                         # Fichiers générés (gitignored)
│   ├── factures-xml/             # XML Factur-X sauvegardés ( suivant la conf ) 
│   ├── factures-pdf/             # PDF Factur-X sauvegardés ( suivant la conf ) 
│   └── test/                     # Fichiers de test
└── resources/
    ├── config/
    │   └── ma-conf.txt           # Configuration émetteur
    ├── fonts/                    # Polices embarquées PDF/A-3
    │   ├── LiberationSans-Regular.ttf
    │   ├── LiberationSans-Bold.ttf
    │   ├── LiberationSans-Italic.ttf
    │   ├── LiberationSans-BoldItalic.ttf
    │   └── LICENSE               # Licence SIL Open Font
    ├── logos/                    # Logos entreprise
    │   ├── sntpk-logo.jpeg       # Si pas de logo, underwork.jpeg sera utilisé
    │   └── underwork.jpeg        # Logo par défaut (fallback)
    ├── profiles/
    │   └── sRGB.icc              # Profil ICC sRGB pour OutputIntent PDF/A-3
    ├── sql/
    │   └── create_table_sent_invoice.sql # si potion base de données à True
    └── templates/                # Templates HTML Jinja2
        ├── invoice_step1.html    # Formulaire infos facture + client
        ├── invoice_step2.html    # Formulaire lignes de facturation
        ├── invoice_step3.html    # Récapitulatif et téléchargement
        └── facturx-xmp.xml       # Modèle métadonnées XMP
```

## Routes Flask

| Méthode | Route                 | Fonction              | Description                                           |
|---------|-----------------------|-----------------------|-------------------------------------------------------|
| GET     | `/`                   | `index()`             | Affiche le formulaire step 1 (infos facture + client) |
| POST    | `/invoice/step1`      | `submit_step1()`      | Valide step 1, stocke en session, retourne JSON       |
| GET     | `/invoice/step2`      | `show_step2()`        | Affiche le formulaire step 2 (lignes de facturation)  |
| POST    | `/invoice`            | `generate_invoice()`  | Valide step 2, génère PDF/XML, redirige vers step 3   |
| GET     | `/invoice/step3`      | `show_step3()`        | Affiche le récapitulatif de la facture générée        |
| GET     | `/invoice/download-pdf`| `download_pdf()`     | Télécharge le PDF Factur-X depuis le stockage         |
| GET     | `/invoice/new`        | `new_invoice()`       | Vide la session et redirige vers step 1               |

## Fonctionnalités

### Interface utilisateur
- ✅ Formulaire en 3 étapes avec navigation fluide
- ✅ Validation temps réel côté client
- ✅ Validation stricte côté serveur
- ✅ Calcul automatique des totaux et récapitulatif TVA
- ✅ Support des rabais par ligne (pourcentage ou montant fixe)
- ✅ Interface responsive (desktop, tablette, mobile)
- ✅ Design moderne avec dégradés et animations

### Génération Factur-X
- ✅ PDF de facture visuel avec ReportLab
- ✅ XML structuré conforme EN 16931 profil EN16931
- ✅ Validation XSD automatique
- ✅ Combinaison PDF + XML avec factur-x
- ✅ Métadonnées PDF/A-3
- ✅ Sauvegarde automatique (XML + PDF)
- ✅ Page récapitulative avec téléchargement PDF
- ✅ Insertion en base PostgreSQL (si `is_db_pg=True`), indépendante de la numérotation auto

### Conformité PDF/A-3
- ✅ Polices **Liberation Sans** embarquées (TTF subset) — zéro référence Helvetica
- ✅ Profil ICC **sRGB** intégré via OutputIntent (`/GTS_PDFA1`)
- ✅ Validé **VeraPDF** PDF/A-3B (146 règles, 0 échec)

### Conformité Factur-X
- ✅ Norme EN 16931 (facturation électronique européenne)
- ✅ Profil Factur-X EN16931 (guideline `urn:cen.eu:en16931:2017`)
- ✅ Structure CrossIndustryInvoice (CII)
- ✅ Validation XSD officielle
- ✅ Conformité Schematron (PEPPOL-EN16931)
- ✅ Compatible avec tous les lecteurs Factur-X

## Format Factur-X

### Profil de conformité

**URN :** `urn:cen.eu:en16931:2017`

Le profil EN16931 (aussi appelé Comfort) est le profil de conformité complet à la norme européenne EN 16931 (Factur-X 1.07, CII D22B).

### Structure XML

Le XML généré respecte la structure CrossIndustryInvoice (CII) avec les namespaces :

```xml
<rsm:CrossIndustryInvoice
  xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
  xmlns:qdt="urn:un:unece:uncefact:data:standard:QualifiedDataType:100"
  xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
  xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">

  <rsm:ExchangedDocumentContext>
    <!-- Profil et version -->
  </rsm:ExchangedDocumentContext>

  <rsm:ExchangedDocument>
    <!-- Numéro, type, date, notes -->
  </rsm:ExchangedDocument>

  <rsm:SupplyChainTradeTransaction>
    <!-- Lignes, parties, totaux -->
  </rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>
```

### Champs du profil EN16931

Le profil EN16931 supporte l'ensemble des champs d'adresse :

**Structure PostalTradeAddress :**
```xml
<ram:PostalTradeAddress>
  <ram:PostcodeCode>75001</ram:PostcodeCode>
  <ram:LineOne>123 rue de la Paix</ram:LineOne>
  <ram:CityName>Paris</ram:CityName>
  <ram:CountryID>FR</ram:CountryID>
</ram:PostalTradeAddress>
```

**Éléments supportés :**
- ✅ `PostcodeCode` : Code postal
- ✅ `LineOne` : Adresse ligne 1 (obligatoire)
- ✅ `CityName` : Ville (obligatoire)
- ✅ `CountryID` : Code pays ISO (obligatoire)

## Flux de génération

```
┌─────────────────────────────────────────────────────────┐
│ 1. Formulaire Step 1 → Collecte données facture/client  │
└───────────────┬─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────────────────┐
│ 2. Formulaire Step 2 → Lignes de facturation + calculs  │
└───────────────┬─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────────────────┐
│ 3. pdf_generator.py → Génère PDF (ReportLab)            │
│    → Polices Liberation Sans embarquées (TTF subset)    │
│    → OutputIntent sRGB avec profil ICC                  │
└───────────────┬─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────────────────┐
│ 4. facturx_generator.py → Génère XML Factur-X (EN16931)  │
│    → Guideline 1.07 D22B, date livraison, Schematron OK │
└───────────────┬─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────────────────┐
│ 5. factur-x.generate_from_binary() → Validation XSD     │
│    → Combine PDF + XML → Métadonnées PDF/A-3            │
└───────────────┬─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────────────────┐
│ 6. Sauvegarde (xml_storage + pdf_storage)               │
│    → Insert en base si is_db_pg=True                    │
└───────────────┬─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────────────────┐
│ 7. Step 3 - Récapitulatif                               │
│    → Résumé, téléchargement PDF, nouvelle facture       │
└─────────────────────────────────────────────────────────┘
```

## Base de données PostgreSQL (optionnel)

### Prérequis

Si `is_db_pg=True`, le driver PostgreSQL doit être installé :

```bash
uv add psycopg2-binary
```

### Activation

1. **Créer `.env` ou `.env.local` :**
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=facturx
DB_USER=postgres
DB_PASSWORD=votre_mot_de_passe
```

2. **Activer dans la configuration :**
```ini
# resources/config/ma-conf.txt
is_db_pg=True
```

L'application vérifiera automatiquement la connexion au démarrage.

### Numérotation automatique des factures

Lorsque `is_num_facturx_auto=True` **et** `is_db_pg=True`, le numéro de facture est généré automatiquement à partir de la base de données.

**Format :** `FAC-YYYY-MM-NNNN`

| Segment  | Description                              | Exemple        |
|----------|------------------------------------------|----------------|
| `FAC`    | Préfixe fixe                             | `FAC`          |
| `YYYY`   | Année en cours                           | `2026`         |
| `MM`     | Mois en cours                            | `02`           |
| `NNNN`   | Entier auto-incrémenté, unique           | `0001`, `0042` |

**Exemples :** `FAC-2026-02-0001`, `FAC-2026-02-0002`, `FAC-2026-03-0001`

**Fonctionnement :**

1. Requête en base pour récupérer le numéro de la facture la plus récente
2. Extraction de l'entier `NNNN` par regex depuis le dernier numéro
3. Incrémentation de +1 et recomposition du nouveau numéro
4. **Verrouillage transactionnel** (lock) de la table pendant toute la génération (XML + PDF + insertion en base) pour garantir l'unicité du numéro en accès concurrent
5. Le lock est relâché une fois l'insertion terminée (commit) ou en cas d'erreur (rollback)

```ini
# resources/config/ma-conf.txt
is_db_pg=True
is_num_facturx_auto=True
```

> **Note :** Si `is_num_facturx_auto=False` (défaut), le numéro de facture est saisi manuellement dans le formulaire step 1.

## Commandes utiles

```bash
# Lancer l'application
uv run python app.py

# Tester la génération Factur-X
uv run python test_facturx.py

# Ajouter une dépendance
uv add <package>

# Mettre à jour les dépendances
uv sync --upgrade

# Nettoyer le cache
uv cache clean

# Vérifier la version Python
uv run python --version
```


## Ressources

- [Factur-X Official](https://fnfe-mpe.org/factur-x/)
- [Norme EN 16931](https://ec.europa.eu/digital-building-blocks/sites/display/DIGITAL/Compliance+with+eInvoicing+standard)
- [factur-x Python Library](https://github.com/akretion/factur-x)
- [ReportLab Documentation](https://www.reportlab.com/docs/reportlab-userguide.pdf)

## Licence

Projet privé SNTPK.

---

**Version :** 1.0.0
**Python :** 3.12+
**Profil Factur-X :** EN16931 (Factur-X 1.07, CII D22B)
**Conformité :** PDF/A-3B (VeraPDF) + XSD + Schematron
**Dernière mise à jour :** 2026-02-09
