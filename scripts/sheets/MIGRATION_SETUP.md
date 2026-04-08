# Configuration et Migration - v2.0 Single-Sheet

Guide complet pour configurer et exécuter la migration vers l'architecture single-sheet.

---

## 📋 Étape 1 : Configuration du Spreadsheet ID

### Option A : Configuration Interactive (Recommandée)

Exécutez le script de configuration qui vous guide étape par étape :

```bash
python scripts/sheets/setup_spreadsheet_id.py
```

**Ce que ça fait:**
1. ✅ Vous demande votre Spreadsheet ID
2. ✅ Valide l'ID fourni
3. ✅ Sauvegarde dans `_shared/config/sheets_config.json`
4. ✅ Affiche les prochaines étapes

### Option B : Configuration Manuelle

1. Ouvrez votre Google Sheet
2. Copiez l'ID depuis l'URL : `https://docs.google.com/spreadsheets/d/**{ID}**/edit`
3. Éditez `_shared/config/sheets_config.json` :
   ```json
   {
     "spreadsheet_id": "YOUR_ACTUAL_ID_HERE",
     ...
   }
   ```

### Option C : Override en Ligne de Commande

```bash
python scripts/sheets/migrate_to_single_sheet.py \
  --spreadsheet-id "YOUR_ID" \
  --dry-run
```

---

## 🔍 Étape 2 : Test de Migration (DRY RUN)

**Important:** Toujours tester d'abord avant une migration en live.

### Avec Spreadsheet ID Configuré

```bash
python scripts/sheets/migrate_to_single_sheet.py --dry-run
```

### Avec Spreadsheet ID en Ligne de Commande

```bash
python scripts/sheets/migrate_to_single_sheet.py \
  --spreadsheet-id "YOUR_ID" \
  --dry-run
```

**Ce qui va se passer:**
1. Lire les 4 feuilles legacy (URLs_Input, Audit_Results, Refresh_Results, Decision_Log)
2. Fusionner les données par URL
3. Mapper vers la nouvelle structure Refreshs_Audit (26 colonnes)
4. **Afficher un aperçu** sans écrire dans le sheet

---

## ✅ Étape 3 : Migration en LIVE

**Attention:** Cette étape modifiera votre Google Sheet !

### Avec Spreadsheet ID Configuré

```bash
python scripts/sheets/migrate_to_single_sheet.py --live
```

### Avec Spreadsheet ID en Ligne de Commande

```bash
python scripts/sheets/migrate_to_single_sheet.py \
  --spreadsheet-id "YOUR_ID" \
  --live
```

**Ce qui va se passer:**
1. ✅ Step 1-5 : Migration des données
2. ✅ **Step 6 : Formatage automatique** (data validation + couleurs)
3. ✅ Summary : Résumé complet avec statistiques

---

## 🎯 Fichiers de Configuration

### `_shared/config/sheets_config.json`

Configuration centralisée pour la migration :

```json
{
  "spreadsheet_id": "YOUR_SPREADSHEET_ID",
  "spreadsheet_name": "Refresh SEO Audit v2.0",
  "description": "Main operational spreadsheet",
  "sheets": {
    "Refreshs_Audit": {
      "type": "primary",
      "columns": 22
    },
    "Decision_Log": {
      "type": "archive"
    },
    "Refresh_Results": {
      "type": "archive"
    }
  }
}
```

**Clés:**
- `spreadsheet_id` : ID du Google Sheet (obligatoire)
- `spreadsheet_name` : Nom affiché (optionnel)
- `sheets` : Informations sur les feuilles

---

## 🚀 Workflow Complet (Recommandé)

```bash
# 1. Configuration interactive
python scripts/sheets/setup_spreadsheet_id.py

# 2. Test de la migration
python scripts/sheets/migrate_to_single_sheet.py --dry-run

# 3. Vérifier les logs et la simulation

# 4. Migration en live
python scripts/sheets/migrate_to_single_sheet.py --live

# 5. Vérifier le sheet dans Google Sheets
# - Ouvrir le sheet
# - Vérifier la feuille "Refreshs_Audit"
# - Tester les menus déroulants (colonnes E-I)
# - Rafraîchir le navigateur pour voir les couleurs
```

---

## 📊 Résumé des Paramètres

| Option | Description | Défaut | Exemple |
|--------|-------------|--------|---------|
| `--spreadsheet-id` | ID du Google Sheet | Depuis config | `--spreadsheet-id "ABC123"` |
| `--service-account` | Chemin service account | Défaut interne | `--service-account "/path/to/creds.json"` |
| `--dry-run` | Mode simulation | True | `--dry-run` |
| `--live` | Mode écriture | False | `--live` |

---

## ✨ Améliorations v2.0

✅ **Auto-Load de Spreadsheet ID**
- Charge depuis `_shared/config/sheets_config.json`
- Peut être overridé en ligne de commande
- Messages d'erreur clairs si non configuré

✅ **Setup Assistant Interactif**
- Script `setup_spreadsheet_id.py` pour configuration facile
- Validation de l'ID
- Sauvegarde automatique

✅ **Migration Step 6 : Formatage Automatique**
- Data Validation (menus déroulants)
- Conditional Formatting (couleurs)
- Texte blanc pour lisibilité PARENT

---

## 🔧 Troubleshooting

### "No spreadsheet_id provided or configured"

**Solution:**
```bash
python scripts/sheets/setup_spreadsheet_id.py
```
Ou modifiez `_shared/config/sheets_config.json`

### "Sheet 'Refreshs_Audit' not found"

**Possible causes:**
- La migration n'a pas créé la feuille (erreur Step 5)
- Le mauvais spreadsheet_id est utilisé

**Solution:**
1. Vérifier le spreadsheet_id : `python scripts/sheets/setup_spreadsheet_id.py`
2. Relancer avec `--dry-run` pour voir les détails

### Les couleurs ne s'affichent pas

**Solution:**
- Rafraîchir le navigateur (F5)
- Les couleurs s'appliquent lors du rechargement

### Erreur de service account

**Solution:**
Vérifier que le fichier credentials existe :
```bash
ls "C:/Users/samue/.credentials/google/google-service-account.json"
```

---

## 📚 Ressources Additionnelles

- [SHEET_FORMATTING.md](./SHEET_FORMATTING.md) - Guide formatage visuel
- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - Fiche rapide
- [README_FORMATTING.md](./README_FORMATTING.md) - Navigation complète

---

## 🎓 Prochaines Étapes Après Migration

1. **Vérification** : Ouvrir le sheet et tester les menus déroulants
2. **Documentation** : Mettre à jour le wiki interne
3. **Formation** : Former les utilisateurs à la nouvelle structure
4. **Archivage** : Renommer les anciennes feuilles avec `_ARCHIVED_DATE`

---

**Version** : 2.0
**Date** : Février 2026
**Status** : ✅ Production Ready
