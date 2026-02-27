1 annuaire
---------------
La documentation mentionnait un outil **"Info Annuaire"** et une API pour ça. Laisse-moi chercher directement.Maintenant cherchons l'endpoint API correspondant dans la référence OpenAPI.La page OpenAPI est rendue dynamiquement. Cherchons le JSON de spec directement.Je vois la section **Directory Entries** dans la sidebar. Cliquons sur "List directory entries".Maintenant regardons **"Get a directory entry"** pour voir comment chercher par SIREN/SIRET.J'ai tout ce qu'il faut. Voici la synthèse complète :

---

## Comment récupérer l'adresse de routage d'un fournisseur sur SuperPDP

### Option 1 — L'outil web (sans code)

Directement sur **https://www.superpdp.tech/outils/info-annuaire**, tu saisis le SIREN et l'outil interroge l'annuaire Peppol pour vérifier si l'entreprise est prête à recevoir des factures électroniques.

---

### Option 2 — Via l'API

**Lister les entrées d'annuaire** de ta propre entreprise :
```bash
GET https://api.superpdp.tech/v1.beta/directory_entries
Authorization: Bearer YOUR_SECRET_TOKEN
```

La réponse retourne notamment le champ clé :
```json
{
  "identifier": "0225:853322915",
  "directory": "peppol",
  "is_replyto": true,
  "status": "pending"
}
```

**Récupérer une entrée par son id interne :**
```bash
GET https://api.superpdp.tech/v1.beta/directory_entries/{id}
Authorization: Bearer YOUR_SECRET_TOKEN
```

---

### Ce que retourne l'`identifier`

C'est exactement la valeur à mettre dans ta balise XML :

```json
"identifier": "0225:853322915"
```
↓ se découpe en :

| Partie | Valeur | Rôle |
|---|---|---|
| `0225` | schemeID | Identifiant du référentiel (SIRET/France) |
| `853322915` | Participant ID | L'adresse de routage (ici SIREN seul) |

Ce qui donne dans ta Facture-X :
```xml
<ram:URIUniversalCommunication>
  <ram:URIID schemeID="0225">853322915</ram:URIID>
</ram:URIUniversalCommunication>
```

> ⚠️ **L'API SuperPDP ne permet pas (encore) de chercher une entreprise tierce par son SIREN/SIRET.** Pour connaître l'adresse d'un fournisseur externe, il faut utiliser l'**outil Info Annuaire** en ligne, ou interroger directement l'annuaire central Peppol via son API publique : `https://directory.peppol.eu`.

2- ramasser les factures reçues
-------------------------------------

