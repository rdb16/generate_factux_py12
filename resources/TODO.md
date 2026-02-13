# Module d'envoi des factures vers SUPER PDP , une plateforme agréée 

La documentation API de SUPER PDP est disponible directement sur leur site technique, avec un guide de démarrage rapide pour le dépôt de factures en environnement sandbox. Elle couvre l'authentification, les formats comme Factur-X/EN 16931, la gestion d'erreurs et les endpoints REST/JSON (OpenAPI).

## Accès à la documentation

- **Page d'accueil documentation** : https://www.superpdp.tech/documentation/ – Guide de démarrage rapide pour envoyer une facture électronique via API en bac à sable.[1]
- **Authentification** : https://www.superpdp.tech/documentation/4 – Détails sur l'auth API (probablement API Key ou JWT, standard pour ce type de PA).[2]
- **Formats supportés (Factur-X, EN 16931)** : https://www.superpdp.tech/documentation/6 – Spécifications pour les factures structurées comme les tiennes (BASIC/COMFORT).[3]
- **Gestion des erreurs** : https://www.superpdp.tech/documentation/5 – Codes HTTP standards (2xx succès, etc.) et réponses détaillées.[4]

## Flux type pour dépôt de facture (d'après docs)

1. **Authentification** : Obtiens un token via endpoint dédié (détails en /documentation/4).[2]
2. **Envoi facture** : POST vers un endpoint dédié (type `/invoices` ou `/send`), avec payload multipart ou JSON contenant ton fichier Factur-X (PDF/A-3 + XML embarqué) et métadonnées (destinataire SIREN/SIRET, etc.). Le guide sandbox te montre un exemple curl complet.[1]
3. **Suivi** : Récupère statuts via GET `/invoices/{id}` ou webhooks (callbacks configurables pour asynchrone).[5]
4. **Sandbox gratuite** : Accès immédiat pour tester sans compte payant, idéal pour prototyper ton intégration Rust/Python.[6]

## Points techniques clés

- **OpenAPI/Swagger** : La doc est interactive (Swagger UI probable), pour générer clients auto (Rust reqwest, Python requests, etc.).[5]
- **Formats** : Factur-X natif (XML EN 16931 validé), UBL/CII pour Peppol si besoin.[3]
- **Erreurs** : Codes HTTP + body JSON explicite (ex. 400 pour Factur-X malformé).[4]

Commence par le guide de démarrage (https://www.superpdp.tech/documen tation/), ça te prendra 10 min pour envoyer ta première Factur-X en sandbox. Si tu rencontres un blocage spécifique (ex. payload exact), partage un snippet de ton Factur-X et je t'aide à mapper l'endpoint.[1]

Sources
[1] Démarrage rapide https://www.superpdp.tech/documentation/
[2] Authentification https://www.superpdp.tech/documentation/4
[3] Formats de facture https://www.superpdp.tech/documentation/6
[4] Erreurs https://www.superpdp.tech/documentation/5
[5] SUPER PDP — Plateforme agréée (PA) API-first & tarifs publics https://www.comparateur-facturation-electronique.fr/produit/super-pdp/
[6] SUPER PDP - francenum.gouv.fr https://www.francenum.gouv.fr/activateurs/super-pdp
[7] OpenAPI Definition and Endpoints https://xytechsystems.github.io/documentation/REST-API%20Guide/OpenAPI%20definition/
[8] Akretion choisit SUPER PDP pour les modules de Odoo ... https://akretion.com/fr/blog/facturation-electronique--akretion-choisit-super-pdp-comme-pdp-pour-odoo-community
[9] REST API Documentation - Real Time Data Ingestion ... https://www.rtdip.io/api/rest_apis/
[10] API PDP : comparatif et guide FacturX https://www.facturx.blog/api-pdp-guide-complet/
