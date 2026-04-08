# Guide: Ajouter les colonnes "To Do" et "recommended_actions" au Spreadsheet

## ⚠️ Étape Critique

Avant d'exécuter le workflow avec la nouvelle implémentation, vous DEVEZ ajouter les colonnes manquantes au Google Sheets.

## 🚀 Méthode 1: Script Automatisé (Recommandé)

Exécutez le script d'ajout de colonnes:

```bash
python scripts/utils/add_sheet_columns.py --spreadsheet-id "1F99FtN8fWQlQm0ZTJphBRz_c64iDs2DvohyHyM2Tk1M"
```

**Ce script va:**
✅ Ajouter la colonne "to_do" après "recommendations"
✅ Ajouter la colonne "recommended_actions"
✅ Créer un dropdown menu (data validation) pour "to_do" avec les options:
   - Aucune action nécessaire
   - Optimiser titres (H1 et H2)
   - Réécriture partielle (mise à jour dates et statistiques)
   - Réécriture totale (contenu obsolète)
   - ⚠️ Redirection 301 (cannibalisation sévère)

**Résultat attendu:**
```
✓ En-têtes actuels (19 colonnes):
  1. url
  2. audit_date
  ...
  19. recommendations
➕ Ajout de colonne 'to_do'
➕ Ajout de colonne 'recommended_actions'
✓ Colonnes mises à jour: 2 cellules
✓ Validation de données ajoutée pour la colonne 'to_do'
✅ Colonnes ajoutées avec succès!
```

---

## 🔧 Méthode 2: Manuellement dans Google Sheets

Si vous préférez ajouter les colonnes manuellement:

### Étape 1: Ouvrir le spreadsheet
- Allez à: https://docs.google.com/spreadsheets/d/1F99FtN8fWQlQm0ZTJphBRz_c64iDs2DvohyHyM2Tk1M/edit
- Cliquez sur l'onglet **"Audit_Results"**

### Étape 2: Ajouter la colonne "to_do"
1. Trouvez la dernière colonne avec un en-tête (après "recommendations")
2. Cliquez sur la colonne suivante (vide)
3. Écrivez dans l'en-tête: **"to_do"**
4. Appuyez sur Entrée

### Étape 3: Ajouter la colonne "recommended_actions"
1. Cliquez sur la colonne suivante (vide)
2. Écrivez dans l'en-tête: **"recommended_actions"**
3. Appuyez sur Entrée

### Étape 4: Ajouter le dropdown menu pour "to_do" (Optionnel mais recommandé)
1. Cliquez sur la cellule de la colonne "to_do" (en-tête)
2. Sélectionnez toute la colonne "to_do" (Data > Data validation)
3. Configurez les options de liste:
   - Aucune action nécessaire
   - Optimiser titres (H1 et H2)
   - Réécriture partielle (mise à jour dates et statistiques)
   - Réécriture totale (contenu obsolète)
   - ⚠️ Redirection 301 (cannibalisation sévère)

---

## ✅ Vérification

Après l'ajout, vérifiez que:

✓ La feuille "Audit_Results" a 21 colonnes (19 + 2 nouvelles)
✓ Les colonnes 20 et 21 s'appellent "to_do" et "recommended_actions"
✓ La colonne "to_do" a un dropdown menu (si vous avez utilisé Méthode 2)

---

## 📊 Exemple de Structure Finale

```
URL | audit_date | ... | recommendations | to_do | recommended_actions
https://example.com/article | 2026-02-10 | ... | "Actualiser données" | "Réécriture partielle (mise à jour dates et statistiques)" | "✓ 5 date(s) mise à jour automatiquement (→2026)"
```

---

## 🔄 Après l'Ajout des Colonnes

Une fois les colonnes ajoutées, vous pouvez exécuter le workflow normalement:

```bash
# Traitement batch
python main.py --mode batch --spreadsheet-id "1F99FtN8fWQlQm0ZTJphBRz_c64iDs2DvohyHyM2Tk1M" --limit 5

# Les colonnes "to_do" et "recommended_actions" seront automatiquement remplies!
```

---

## 🐛 Dépannage

### Erreur: "Google Sheets API non disponible"
- Vérifiez que le fichier de credentials est présent: `C:/Users/samue/.credentials/google/google-service-account.json`
- Vérifiez que vous avez les droits d'accès au spreadsheet

### Les colonnes ne s'affichent pas
- Actualisez la page (F5)
- Vérifiez que vous êtes sur la feuille "Audit_Results"
- Scrollez à droite pour voir les nouvelles colonnes

### Le dropdown ne fonctionne pas
- Utilisez le script automatisé (Méthode 1)
- Ou reconfigurer manuellement la validation de données (Data > Data validation)

---

## 📝 Notes

- Le script crée automatiquement une **data validation** pour le dropdown menu
- Les colonnes sont ajoutées à la FIN de la feuille (après "recommendations")
- Les données existantes ne sont PAS modifiées
- Le script est **idempotent** (peut être exécuté plusieurs fois sans problème)
