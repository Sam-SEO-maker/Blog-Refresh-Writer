# Sheet Formatting - Fiche de Référence Rapide

## 🎨 Palette de Couleurs

### Colonne E : Post Type (Architecture Sémantique)
```
🔺 PARENT       Violet foncé    #4B0082   (texte blanc - IMPORTANT pour lisibilité)
📄 CHILD        Violet clair    #DDA0DD
🔲 STANDALONE   Gris neutre     #C0C0C0
```

### Colonne F : Action Blogpost
```
⬜ NO ACTION       Gris           #CCCCCC
🔵 PARTIAL REF    Bleu clair     #ADD8E6
🟡 REFRESH TITLES Jaune          #FFFF00
🟠 FULL REFRESH   Orange         #FFA500
```

### Colonne G : Status
```
⬜ NO ACTION       Gris           #CCCCCC
🟢 TITLES DONE    Vert clair     #90EE90
🟢 CONTENT DONE   Vert foncé     #228B22
```

### Colonnes H & I : Audits (GSC/SERP)
```
🟡 AUDITING       Jaune          #FFFF00
🟢 DONE           Vert           #00FF00
🔴 FAILED         Rouge          #FF0000
```

---

## 🚀 Lancer la Mise en Forme

### 1️⃣ Standalone Script (Plus Simple ✨ RECOMMANDÉ)
```bash
cd "c:\Users\samue\OneDrive\Bureau\Claude Code\Super Refresh Writer"
python scripts/sheets/apply_sheet_formatting.py
```
✅ Auto-charge spreadsheet_id depuis config
✅ Applique menus déroulants + couleurs
✅ Aucune migration, aucun risque

**Ou avec ID explicite:**
```bash
python scripts/sheets/apply_sheet_formatting.py --spreadsheet-id 1F99FtN8fWQlQm0ZTJphBRz_c64iDs2DvohyHyM2Tk1M
```

### 2️⃣ Avec Migration (Complet)
```bash
python scripts/sheets/migrate_to_single_sheet.py \
  --spreadsheet-id YOUR_SHEET_ID \
  --live
```
✅ Migre données + met en forme automatiquement (Step 6)

### 3️⃣ One-Liner Python
```bash
python -c "
from scripts.sheets.sheets_client import SheetsClient
client = SheetsClient('YOUR_SHEET_ID')
result = client.setup_sheet_formatting()
print('✓ Done!' if result else '✗ Failed!')
"
```

### 4️⃣ Depuis Python Script
```python
from scripts.sheets.sheets_client import SheetsClient

client = SheetsClient(spreadsheet_id="YOUR_ID")
if client.setup_sheet_formatting():
    print("✓ Mise en forme appliquée avec succès")
else:
    print("✗ Erreur lors de la mise en forme")
```

---

## 📋 Validation de Données

Chaque colonne a un menu déroulant avec validation stricte:

| Colonne | Options | Validation |
|---------|---------|-----------|
| **E** | PARENT, CHILD, STANDALONE | ✅ Stricte |
| **F** | NO ACTION, PARTIAL REFRESH, REFRESH TITLES, FULL REFRESH | ✅ Stricte |
| **G** | NO ACTION, TITLES DONE, CONTENT DONE | ✅ Stricte |
| **H** | AUDITING, DONE, FAILED | ✅ Stricte |
| **I** | AUDITING, DONE, FAILED | ✅ Stricte |

➡️ **Strict Mode** = Pas de saisie libre, seulement les valeurs de la liste

---

## 🎯 Utilisation Typique

### Workflow d'un Article

```
1. Nouvelle URL ajoutée
   ↓
2. Colonne E : Choisir PARENT/CHILD/STANDALONE
   (Violet foncé/clair = architecture visible)
   ↓
3. Colonne H : Audit GSC = AUDITING (Jaune)
   ↓
4. Audit termine → H = DONE (Vert)
   ↓
5. Colonne F : Action décidée → PARTIAL/FULL REFRESH (Orange/Jaune)
   ↓
6. Colonne G : Status = TITLES DONE ou CONTENT DONE (Vert)
```

---

## ⚙️ Architecture Technique

- **API** : Google Sheets v4 (Batch Update)
- **Validations** : 5 (colonnes E, F, G, H, I)
- **Formatages** : 13 (3 pour E + 4 pour F + 3 pour G + 3 pour H + 3 pour I)
- **Total requêtes** : ~18 appels API
- **Temps d'exécution** : 1-2 secondes

---

## 🐛 Troubleshooting

| Problème | Solution |
|----------|----------|
| Les couleurs ne s'affichent pas | Rafraîchir le navigateur (F5) |
| Menu déroulant n'apparaît pas | Vérifier que vous cliquez dans une cellule de données (pas header) |
| "Sheet not found" | Vérifier que la feuille "Refreshs_Audit" existe |
| Erreur API permission | Vérifier les permissions du service account |

---

## 📚 Références

- [Documentation Complète](./SHEET_FORMATTING.md)
- [SheetsClient](./sheets_client.py#L960)
- [Migration Script](./migrate_to_single_sheet.py#L289-L300)

---

**Version** : 2.0
**Mise à jour** : Février 2026
**Type** : Fiche de Référence Rapide
