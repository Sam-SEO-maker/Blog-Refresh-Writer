# 📊 Sheet Formatting - Guide Complet

Bienvenue dans la mise en forme visuelle avancée du sheet **Refreshs_Audit** pour le workflow v2.0 du projet **Super Refresh Writer**.

## 🗺️ Navigation

### 📖 Pour Comprendre
**👉 Commencez par :** [SHEET_FORMATTING.md](./SHEET_FORMATTING.md)
- Vue d'ensemble complète
- Palettes de couleurs détaillées (Hex + RGB)
- Architecture technique
- Workflow visuel
- Guide de troubleshooting

### ⚡ Pour Agir Rapidement
**👉 Consultez :** [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)
- Palette de couleurs résumée
- Commandes d'utilisation rapide
- Tableau de validation
- Workflow typique

### 🔧 Pour l'Implémentation
**👉 Référencez :** [sheets_client.py](./sheets_client.py#L960)
- Méthode `setup_sheet_formatting()`
- Data Validation (menus déroulants)
- Conditional Formatting (couleurs)

**👉 Pour la migration :** [migrate_to_single_sheet.py](./migrate_to_single_sheet.py#L289)
- Étape 6 : Formatage automatique

---

## 🎯 Utilisation Rapide

### 1️⃣ Migration Automatique (Recommandé)
```bash
python scripts/sheets/migrate_to_single_sheet.py \
  --spreadsheet-id YOUR_SHEET_ID \
  --live
```
✅ La mise en forme s'applique automatiquement à l'étape 6

### 2️⃣ Formatage Manuel
```bash
python -c "
from scripts.sheets.sheets_client import SheetsClient
SheetsClient('YOUR_SHEET_ID').setup_sheet_formatting()
"
```

---

## 🎨 Palette Visuelle

| Colonne | Type | Valeurs | Couleurs |
|---------|------|---------|----------|
| **E** | Post Type | PARENT, CHILD, STANDALONE | Violet, Violet clair, Gris |
| **F** | Actions | NO ACTION, PARTIAL, TITLES, FULL | Gris, Bleu, Jaune, Orange |
| **G** | Statuts | NO ACTION, TITLES DONE, CONTENT DONE | Gris, Vert clair, Vert foncé |
| **H** | Audit GSC | AUDITING, DONE, FAILED | Jaune, Vert, Rouge |
| **I** | Audit SERP | AUDITING, DONE, FAILED | Jaune, Vert, Rouge |

---

## ✨ Highlights Principaux

### Architecture Sémantique (Col E)
- 🔺 **PARENT** : Violet foncé + texte blanc
  - Articles piliers (guides complets)
  - Base des cocons sémantiques

- 📄 **CHILD** : Violet clair
  - Articles satellites pour le maillage
  - Liés aux articles PARENT

- 🔲 **STANDALONE** : Gris neutre
  - Articles isolés
  - À optimiser pour maillage?

### Workflow Visuel
- 🟡 **AUDITING** : Travail en cours (jaune)
- 🟢 **DONE** : Terminé (vert)
- 🔴 **FAILED** : Erreur (rouge)

---

## 📚 Fichiers dans ce Répertoire

```
scripts/sheets/
├── sheets_client.py              ← Classes + setup_sheet_formatting()
├── migrate_to_single_sheet.py    ← Script de migration (Step 6)
├── SHEET_FORMATTING.md           ← Documentation complète ⭐
├── QUICK_REFERENCE.md            ← Fiche rapide ⭐
├── README_FORMATTING.md          ← Ce fichier (index)
└── [autres fichiers]
```

---

## 🚀 Déploiement Recommandé

### Phase 1 : Préparation
1. Lire [SHEET_FORMATTING.md](./SHEET_FORMATTING.md)
2. Vérifier la structure du sheet source

### Phase 2 : Exécution
```bash
# Test en dry-run
python scripts/sheets/migrate_to_single_sheet.py \
  --spreadsheet-id YOUR_ID \
  --dry-run

# Migration en live
python scripts/sheets/migrate_to_single_sheet.py \
  --spreadsheet-id YOUR_ID \
  --live
```

### Phase 3 : Validation
1. Vérifier que le sheet Refreshs_Audit a été créé
2. Vérifier les menus déroulants dans les colonnes
3. Vérifier l'application des couleurs
4. Rafraîchir le navigateur si nécessaire

---

## 💡 Tips & Tricks

### Pour les Administrateurs
- Les couleurs se mettent à jour **en temps réel** lors de la saisie
- Les menus déroulants sont **strictement validés** (pas de saisie libre)
- Utilisez [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) comme poster de bureau

### Pour les Opérateurs
- Violet = Architecture sémantique (cocons)
- Jaune = Actions en cours (AUDITING)
- Vert = Travail complété (DONE)
- Rouge = Erreur nécessitant attention (FAILED)

### Pour les Développeurs
- La méthode `setup_sheet_formatting()` utilise l'API Google Sheets v4
- 18 appels API au total (5 validations + 13 conditionnels)
- Erreurs non-bloquantes (continue même si un formatage échoue)

---

## 🆘 Support & Troubleshooting

### Problème : Les couleurs ne s'affichent pas
**Solution :** Rafraîchir le navigateur (F5)

### Problème : Menu déroulant n'apparaît pas
**Solution :** Vérifier que vous cliquez dans une cellule de données (pas header)

### Problème : "Sheet not found"
**Solution :** Vérifier que la feuille "Refreshs_Audit" existe

### Problème : Erreur API
**Solution :** Vérifier les permissions du service account

👉 **Consultez :** [SHEET_FORMATTING.md - Troubleshooting](./SHEET_FORMATTING.md#troubleshooting)

---

## 📞 Questions Fréquentes

**Q: Puis-je ajouter d'autres colonnes au formatage?**
A: Oui, modifiez `setup_sheet_formatting()` dans sheets_client.py

**Q: Comment les couleurs sont-elles appliquées?**
A: Via Google Sheets Conditional Formatting avec formules EXACT()

**Q: Les menus déroulants bloquent la saisie?**
A: Oui, strict mode activé. Seules les valeurs de la liste sont acceptées.

**Q: Quand la mise en forme s'applique?**
A: À chaque création de sheet (migration) ou sur demande manuelle

**Q: Peut-on modifier les couleurs?**
A: Oui, dans la méthode `setup_sheet_formatting()` (valeurs RGB)

---

## 📋 Checklist de Déploiement

- [ ] Lire la documentation (SHEET_FORMATTING.md)
- [ ] Tester en dry-run
- [ ] Vérifier les permissions
- [ ] Exécuter la migration en live
- [ ] Vérifier les menus déroulants
- [ ] Vérifier l'application des couleurs
- [ ] Documenter dans le wiki interne
- [ ] Former les utilisateurs

---

## 🎓 Ressources

- [CLAUDE.md](../../../CLAUDE.md) - Guide opérationnel complet
- [Google Sheets API Docs](https://developers.google.com/sheets/api)
- [Conditional Formatting Guide](https://support.google.com/docs/answer/78413)

---

## 🔄 Versioning

| Version | Date | Changements |
|---------|------|------------|
| 2.0 | Février 2026 | ✅ Implémentation complète avec Col E |
| 1.0 | Janvier 2026 | Colonnes F, G, H, I (version initiale) |

---

**Dernière mise à jour** : Février 2026
**Responsable** : Claude Automation
**Statut** : ✅ Production Ready
