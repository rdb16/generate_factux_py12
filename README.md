# Generate-FacturX-PY

Application Flask pour générer des factures au format Factur-X (norme EN 16931).

## Description

Ce projet permet de créer des factures électroniques conformes au standard Factur-X, le format hybride franco-allemand basé sur PDF/A-3 avec XML embarqué.

Une interface web en deux étapes guide l'utilisateur :

1. **Étape 1 - Informations générales** : numéro de facture, dates, devise, informations client (raison sociale, SIRET, TVA intracommunautaire, adresse)
2. **Étape 2 - Lignes de facturation** : description, quantité, prix unitaire HT, taux de TVA, rabais (en % ou montant fixe)

Le système calcule automatiquement les totaux HT, TVA par taux, et TTC, puis génère un fichier XML conforme au profil Factur-X BASIC.

## Prérequis

- Python 3.14+
- [uv](https://github.com/astral-sh/uv) (gestionnaire de paquets)

## Installation

```bash
# Cloner le projet
git clone <url-du-repo>
cd Generate-FacturX-PY

# Installer les dépendances
uv sync
```

## Lancement

```bash
uv run python app.py
```

L'application sera accessible sur `http://localhost:5000`

## Structure du projet

```
Generate-FacturX-PY/
├── app.py                 # Application Flask principale
├── facturx_generator.py   # Générateur XML Factur-X
├── pyproject.toml         # Configuration du projet et dépendances
└── resources/
    ├── logos/             # Logos pour l'interface
    └── templates/         # Templates HTML Jinja2
        ├── invoice_step1.html
        ├── invoice_step2.html
        └── facturx-xmp.xml
```

## Fonctionnalités

- Formulaire multi-étapes avec validation côté serveur
- Calcul automatique des totaux et récapitulatif TVA
- Support des rabais par ligne (pourcentage ou montant fixe)
- Génération XML conforme Factur-X profil BASIC
- Interface responsive

## Format Factur-X

Le XML généré respecte la structure CrossIndustryInvoice (CII) avec les namespaces :
- `rsm` : CrossIndustryInvoice
- `ram` : ReusableAggregateBusinessInformationEntity
- `udt` : UnqualifiedDataType

Profil de conformité : **urn:factur-x.eu:1p0:basic**

## Licence

Projet privé SNTPK.
