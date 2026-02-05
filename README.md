# Generate-FacturX-PY

Application Flask pour générer des factures électroniques au format Factur-X (norme EN 16931).

## Description

Ce projet permet de créer des **factures électroniques conformes** au standard Factur-X, le format hybride franco-allemand basé sur PDF/A-3 avec XML embarqué.

Le système génère des **PDF Factur-X complets** :
- PDF de facture visuel (généré avec ReportLab)
- XML structuré conforme EN 16931 (profil BASIC)
- Validation XSD officielle
- PDF/A-3 avec métadonnées XMP

### Interface web en deux étapes

1. **Étape 1 - Informations générales**
   - Numéro de facture, type de document, devise
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

## Prérequis

- **Python 3.12+** (⚠️ Python 3.14 non supporté - voir section Migration)
- [uv](https://github.com/astral-sh/uv) (gestionnaire de paquets moderne)

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
    "factur-x>=3.15",         # Génération PDF Factur-X
    "reportlab>=4.4.9",       # Génération PDF
]
```

## Configuration

### 1. Fichier de configuration émetteur

Créer `resources/config/ma-conf.txt` :

```ini
# Émetteur
name=Votre Entreprise SARL
address=123 rue de la Paix, 75001 Paris
siren=123456789
siret=12345678901234
num_tva=FR12345678901
bic=BNPAFRPPXXX

# Logo (optionnel)
logo=./resources/logos/mon-logo.png

# Stockage
xml_storage=./data/factures-xml
pdf_storage=./data/factures-pdf

# Base de données PostgreSQL (optionnel)
is_db_pg=False
```

### 2. Validation au démarrage

L'application valide automatiquement au démarrage :
- ✅ Format SIRET (14 chiffres)
- ✅ Format SIREN (9 chiffres)
- ✅ Cohérence SIREN/SIRET
- ✅ Format BIC (8 ou 11 caractères)
- ✅ Format TVA intracommunautaire
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
============================================================
TEST GÉNÉRATION PDF FACTUR-X
============================================================

[1/4] Génération du PDF de base avec ReportLab...
✓ PDF généré: 11 807 bytes

[2/4] Génération du XML Factur-X...
✓ XML généré: 6 315 caractères

[3/4] Combinaison PDF + XML avec factur-x...
✓ PDF Factur-X généré: 24 653 bytes

[4/4] Sauvegarde du PDF Factur-X...
✓ PDF sauvegardé: data/test/test-facturx.pdf
✓ XML sauvegardé: data/test/test-facturx.xml

[INFO] factur-x XML file successfully validated against XSD
============================================================
```

## Structure du projet

```
Generate-FacturX-PY/
├── app.py                    # Application Flask principale
├── facturx_generator.py      # Générateur XML Factur-X (profil BASIC)
├── pdf_generator.py          # Générateur PDF avec ReportLab
├── test_facturx.py          # Script de test de génération
├── pyproject.toml           # Configuration uv et dépendances
├── uv.lock                  # Verrouillage des versions
├── .python-version          # Version Python (3.12)
├── data/                    # Fichiers générés
│   ├── factures-xml/        # XML sauvegardés
│   ├── factures-pdf/        # PDF Factur-X sauvegardés
│   └── test/                # Fichiers de test
└── resources/
    ├── config/
    │   └── ma-conf.txt      # Configuration émetteur
    ├── logos/               # Logos entreprise
    └── templates/           # Templates HTML Jinja2
        ├── invoice_step1.html
        ├── invoice_step2.html
        └── facturx-xmp.xml
```

## Fonctionnalités

### Interface utilisateur
- ✅ Formulaire multi-étapes avec navigation fluide
- ✅ Validation temps réel côté client
- ✅ Validation stricte côté serveur
- ✅ Calcul automatique des totaux et récapitulatif TVA
- ✅ Support des rabais par ligne (pourcentage ou montant fixe)
- ✅ Interface responsive (desktop, tablette, mobile)
- ✅ Design moderne avec dégradés et animations

### Génération Factur-X
- ✅ PDF de facture visuel avec ReportLab
- ✅ XML structuré conforme EN 16931 profil BASIC
- ✅ Validation XSD automatique
- ✅ Combinaison PDF + XML avec factur-x
- ✅ Métadonnées PDF/A-3
- ✅ Sauvegarde automatique (XML + PDF)

### Conformité
- ✅ Norme EN 16931 (facturation électronique européenne)
- ✅ Profil Factur-X BASIC
- ✅ Structure CrossIndustryInvoice (CII)
- ✅ Validation XSD officielle
- ✅ Compatible avec tous les lecteurs Factur-X

## Format Factur-X

### Profil de conformité

**URN :** `urn:factur-x.eu:1p0:basic`

Le profil BASIC est un sous-ensemble du profil EN16931 adapté aux factures simples.

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

### Contraintes du profil BASIC

Le profil BASIC impose certaines limitations sur la structure des adresses :

**Structure PostalTradeAddress autorisée :**
```xml
<ram:PostalTradeAddress>
  <ram:LineOne>123 rue de la Paix</ram:LineOne>
  <ram:CityName>Paris</ram:CityName>
  <ram:CountryID>FR</ram:CountryID>
</ram:PostalTradeAddress>
```

**Éléments supportés :**
- ✅ `LineOne` : Adresse ligne 1 (obligatoire)
- ✅ `CityName` : Ville (obligatoire)
- ✅ `CountryID` : Code pays ISO (obligatoire)

**Éléments NON supportés dans BASIC :**
- ❌ `PostcodeCode` : Code postal
- ❌ `LineTwo`, `LineThree` : Lignes supplémentaires

ℹ️ **Note :** Le code postal est collecté dans le formulaire mais n'est pas inclus dans le XML BASIC. Pour utiliser tous les champs d'adresse, il faut passer au profil EN16931 ou EXTENDED.

## Flux de génération

```
┌─────────────────────────────────────────────────────────┐
│ 1. Formulaire Step 1 → Collecte données facture/client │
└───────────────┬─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────────────────┐
│ 2. Formulaire Step 2 → Lignes de facturation + calculs │
└───────────────┬─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────────────────┐
│ 3. pdf_generator.py → Génère PDF visuel (ReportLab)    │
└───────────────┬─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────────────────┐
│ 4. facturx_generator.py → Génère XML Factur-X (BASIC)  │
└───────────────┬─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────────────────┐
│ 5. factur-x.generate_from_binary() → Validation XSD    │
│    → Combine PDF + XML → Métadonnées PDF/A-3           │
└───────────────┬─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────────────────┐
│ 6. Sauvegarde (xml_storage + pdf_storage)              │
│    → Téléchargement du PDF Factur-X                    │
└─────────────────────────────────────────────────────────┘
```

## Migration Python 3.14 → 3.12

⚠️ **Important :** Ce projet nécessite Python 3.12 (et non 3.14).

### Raison de la migration

La bibliothèque `lxml` (dépendance de `factur-x`) nécessite une version compatible :
- `factur-x-ng` (non maintenu) dépend de `lxml==4.6.3` (2021)
- `lxml==4.6.3` ne compile pas avec Python 3.14 (`longintrepr.h` introuvable)
- Solution : Utiliser `factur-x` officiel avec `lxml>=6.0.2` sur Python 3.12

### Commandes de migration

```bash
# Downgrade vers Python 3.12
uv python pin 3.12

# Réinstaller les dépendances
uv sync

# Vérifier la version
uv run python --version
# Python 3.12.7
```

## Base de données PostgreSQL (optionnel)

Pour activer le support PostgreSQL :

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

3. **Installer psycopg2 :**
```bash
uv add psycopg2-binary
```

L'application vérifiera automatiquement la connexion au démarrage.

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

## Troubleshooting

### Erreur de compilation lxml

```
fatal error: 'longintrepr.h' file not found
```

**Solution :** Utiliser Python 3.12 (voir section Migration)

### Erreur de validation XSD

```
The XML file is invalid against the XML Schema Definition
Element 'PostcodeCode': This element is not expected
```

**Solution :** Le code postal n'est pas supporté dans le profil BASIC. Vérifier que `PostcodeCode` n'est pas dans le XML généré.

### Fichier de configuration introuvable

```
FileNotFoundError: Fichier de configuration introuvable
```

**Solution :** Créer `resources/config/ma-conf.txt` avec les informations de l'émetteur.

### Logo introuvable

```
[WARNING] Logo introuvable: [...], utilisation du logo par défaut
```

**Solution :** Vérifier le chemin du logo dans `ma-conf.txt` ou laisser vide pour utiliser le logo par défaut.

## Roadmap

- [ ] Support du profil EN16931 (avec PostcodeCode)
- [ ] Support du profil EXTENDED
- [ ] Export en ZUGFeRD (équivalent allemand)
- [ ] Ajout d'une API REST
- [ ] Support multi-devises avancé
- [ ] Templates de facture personnalisables
- [ ] Génération de devis (non-Factur-X)
- [ ] Historique et recherche de factures

## Ressources

- [Factur-X Official](https://fnfe-mpe.org/factur-x/)
- [Norme EN 16931](https://ec.europa.eu/digital-building-blocks/sites/display/DIGITAL/Compliance+with+eInvoicing+standard)
- [factur-x Python Library](https://github.com/akretion/factur-x)
- [ReportLab Documentation](https://www.reportlab.com/docs/reportlab-userguide.pdf)

## Licence

Projet privé SNTPK.

---

**Version :** 0.1.1
**Python :** 3.12+
**Profil Factur-X :** BASIC
**Dernière mise à jour :** 2026-02-05
