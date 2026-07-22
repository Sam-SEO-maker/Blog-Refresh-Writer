# Sheet Formatting Configuration (v2.0)

## Overview

La méthode `setup_sheet_formatting()` configure automatiquement la mise en forme visuelle du sheet **Refreshs_Audit** avec:
- **Data Validation** : Menus déroulants pour saisie contrôlée
- **Conditional Formatting** : Couleurs de fond basées sur les valeurs

## Colonnes configurées

### Colonne E : `post_type` (Architecture Sémantique - Cocons)

| Valeur | Couleur | Texte | Hex | RGB | Signification |
|--------|---------|-------|-----|-----|---------------|
| PARENT | Violet foncé | Blanc | #4B0082 | (0.294, 0.0, 0.510) | 🔺 Article pilier (guide complet) |
| CHILD | Violet clair | Noir | #DDA0DD | (0.866, 0.627, 0.866) | 📄 Article satellite (maillage) |
| STANDALONE | Gris neutre | Noir | #C0C0C0 | (0.753, 0.753, 0.753) | 🔲 Article isolé (pas de cocon) |

**Impact**: Identifie rapidement la position de l'article dans l'architecture sémantique (cocons). Essentiel pour:
- Valider le maillage PARENT → CHILD
- Identifier les articles orphelins
- Gérer les structures d'articles

### Colonne F : `action_blogpost` (Actions de Refresh)

| Valeur | Couleur | Hex | RGB |
|--------|---------|-----|-----|
| NO ACTION | Gris | #CCCCCC | (0.8, 0.8, 0.8) |
| PARTIAL REFRESH | Bleu clair | #ADD8E6 | (0.678, 0.847, 0.902) |
| REFRESH TITLES | Jaune | #FFFF00 | (1.0, 1.0, 0.0) |
| FULL REFRESH | Orange | #FFA500 | (1.0, 0.647, 0.0) |

### Colonne G : `status` (Statuts de Traitement)

| Valeur | Couleur | Hex | RGB |
|--------|---------|-----|-----|
| NO ACTION | Gris | #CCCCCC | (0.8, 0.8, 0.8) |
| TITLES DONE | Vert clair | #90EE90 | (0.565, 0.933, 0.565) |
| CONTENT DONE | Vert foncé | #228B22 | (0.133, 0.545, 0.133) |

### Colonne H : `audit_gsc` (Audit Google Search Console)

| Valeur | Couleur | Hex | RGB |
|--------|---------|-----|-----|
| AUDITING | Jaune | #FFFF00 | (1.0, 1.0, 0.0) |
| DONE | Vert | #00FF00 | (0.0, 1.0, 0.0) |
| FAILED | Rouge | #FF0000 | (1.0, 0.0, 0.0) |

### Colonne I : `audit_serp` (Audit SERP)

| Valeur | Couleur | Hex | RGB |
|--------|---------|-----|-----|
| AUDITING | Jaune | #FFFF00 | (1.0, 1.0, 0.0) |
| DONE | Vert | #00FF00 | (0.0, 1.0, 0.0) |
| FAILED | Rouge | #FF0000 | (1.0, 0.0, 0.0) |

## Installation et Utilisation

### Option 1 : Lors de la Migration (Recommandé)

La méthode `setup_sheet_formatting()` est appelée **automatiquement** lors de la migration 4-sheet → single-sheet:

```bash
python scripts/sheets/migrate_to_single_sheet.py \
  --spreadsheet-id YOUR_SHEET_ID \
  --live
```

**Workflow:**
1. ✅ Migration des données (Étapes 1-5)
2. ✅ **Setup de la mise en forme** (Étape 6) ← Formatage automatique
3. ✅ Summary et recommendations

### Option 2 : Mise en Place Manuelle

```python
from scripts.sheets.sheets_client import SheetsClient

# Initialiser le client
sheets_client = SheetsClient("YOUR_SPREADSHEET_ID")

# Appliquer la mise en forme
if sheets_client.setup_sheet_formatting():
    print("✓ Mise en forme appliquée avec succès")
else:
    print("✗ Erreur lors de la mise en forme")
```

## Détails Techniques

### Data Validation
- **Type**: `ONE_OF_LIST` (listes déroulantes)
- **Strict Mode**: Activé (saisie validée)
- **Messages**: Personnalisés par colonne
- **Plage**: À partir de la ligne 2 (row index 1)

### Conditional Formatting
- **Type**: Règles personnalisées basées sur formules EXACT()
- **Format**: Couleurs de fond + texte gras
- **Application**: Mise à jour **en temps réel** lors de la saisie

### API Utilisée
- Google Sheets API v4
- Batch Update avec `batchUpdate()`
- Nombre de requêtes: ~22 (5 validations + 3+4+3+3 conditional formatting rules = 13)

## Logs et Monitoring

Lors de l'exécution, vous verrez:

```
Step 6: Setting up sheet formatting...
✓ Mise en forme appliquée au sheet Refreshs_Audit
  Colonne E (post_type - Architecture sémantique):
    ✓ Data Validation (3 options: PARENT, CHILD, STANDALONE)
    ✓ Conditional Formatting:
      - PARENT: Violet foncé #4B0082 (texte blanc)
      - CHILD: Violet clair #DDA0DD
      - STANDALONE: Gris neutre #C0C0C0
  Colonne F (action_blogpost):
    ✓ Data Validation (4 options)
    ✓ Conditional Formatting (Gris, Bleu, Jaune, Orange)
  Colonne G (status):
    ✓ Data Validation (3 options)
    ✓ Conditional Formatting (Gris, Vert clair, Vert foncé)
  Colonne H (audit_gsc):
    ✓ Data Validation (3 options)
    ✓ Conditional Formatting (Jaune, Vert, Rouge)
  Colonne I (audit_serp):
    ✓ Data Validation (3 options)
    ✓ Conditional Formatting (Jaune, Vert, Rouge)
```

## Avantages de la Mise en Place

### 🎨 Avantages Visuels
- Identification rapide des statuts (couleur à coup d'œil)
- Menus déroulants pour saisie sans erreur
- Suivi du workflow visuel intuitif

### ✅ Avantages Opérationnels
- Validation des données côté sheet (pas d'erreurs de saisie)
- Cohérence des valeurs garantie
- Documentation visuelle du workflow

### 🔄 Workflow Visuel Complet

```
┌──────────────────────────────────────────────────────────────────────┐
│ REFRESHS_AUDIT SHEET - COMPLETE VISUAL WORKFLOW                      │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Col E: POST_TYPE          Col F: ACTION         Col G: STATUS      │
│  (Architecture)            (Quelle action?)      (État du traitement?)
├────────────────┼──────────────────┼──────────────────────────────────┤
│ 🔺 PARENT      │ NO ACTION (Gris) │ NO ACTION (Gris)               │
│ (Violet foncé) │                  │                                 │
├────────────────┤ PARTIAL REFRESH  │ TITLES DONE (Vert clair)       │
│ 📄 CHILD       │ (Bleu clair)     │                                 │
│ (Violet clair) │                  │ CONTENT DONE (Vert foncé)      │
├────────────────┤ REFRESH TITLES   │                                 │
│ 🔲 STANDALONE  │ (Jaune)          │                                 │
│ (Gris neutre)  │                  │                                 │
│                │ FULL REFRESH     │                                 │
│                │ (Orange)         │                                 │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Col H: AUDIT GSC          Col I: AUDIT SERP                       │
│  (GSC audit status?)       (SERP audit status?)                     │
├─────────────────┼──────────────────────────────────────────────────┤
│ AUDITING (Jaune)│ AUDITING (Jaune)                                 │
│ DONE (Vert)     │ DONE (Vert)                                      │
│ FAILED (Rouge)  │ FAILED (Rouge)                                   │
└──────────────────────────────────────────────────────────────────────┘

Légende:
─────────────────
🔺 PARENT     = Article pilier (guide complet), à partir duquel
              s'articulent les articles CHILD via un cocon sémantique

📄 CHILD      = Article satellite, lié au PARENT pour renforcer
              le maillage interne et la structure du cocon

🔲 STANDALONE = Article isolé, pas de lien cocon identifié ou
              article indépendant de la structure sémantique
```

## Dépendances

- ✅ Google Sheets API v4 (déjà configurée)
- ✅ Service Account Credentials (déjà en place)
- ✅ google-auth-oauthlib, google-auth-httplib2, google-api-python-client

## Troubleshooting

### "Sheet 'Refreshs_Audit' not found"
→ Assurez-vous que la migration s'est bien déroulée et que la feuille existe

### "Sheet formatting setup failed"
→ Vérifiez que le service account a les permissions `https://www.googleapis.com/auth/spreadsheets`

### Les couleurs ne s'appliquent pas
→ Google Sheets met à jour les couleurs au chargement de la page. Rafraîchissez votre navigateur (F5)

## Références

- [SheetsClient Implementation](./sheets_client.py#L964)
- [Migration Script](./migrate_to_single_sheet.py#L289-L300)
- [CLAUDE.md - Architecture](../../../CLAUDE.md#architecture-multi-site)

---

**Version**: 2.0
**Date**: Février 2026
**Mainteneur**: Claude Automation
