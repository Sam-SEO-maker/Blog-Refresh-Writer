# Workflow Automatisé v2.0

## 🚀 Mode `batch-workflow-auto`

Ce nouveau mode exécute **automatiquement** les 4 étapes du workflow de refresh SEO sans intervention manuelle, rendant le processus **scalable** et **production-ready**.

---

## 📊 Les 4 Étapes Automatiques

### **Step 1: Audit GSC**
- ✅ Remplit colonnes **H, J-L, W**
- 📊 Métriques GSC (impressions, clicks, CTR)
- 🔍 Diagnostic d'indexation détaillé (colonne W)
- ⚠️ Détection des URLs 404, redirections, problèmes d'indexation

### **Step 2: Audit SERP**
- ✅ Remplit colonnes **I, M-N**
- 🔎 People Also Ask (PAA) questions
- 🎯 Secondary keywords (top 10)
- 📈 Analyse de la concurrence TOP 3

### **Step 3: Decision Engine**
- ✅ Remplit colonnes **F, Q-U**
- 🎯 Action décidée (NO ACTION, PARTIAL REFRESH, REFRESH TITLES, FULL REFRESH)
- 📝 Métriques de contenu (word count, images, liens internes)
- 🔗 Détection de cannibalisation

### **Step 4: Batch Refresh** (optionnel)
- ✅ Remplit colonnes **G, O-P**
- ✍️ Exécution automatique des refreshs selon l'action décidée
- 🔄 Extraction des H2 du contenu refreshed
- ✅ Validation et restauration des assets (Règle d'Or)

---

## 💻 Utilisation

### **Commande de Base**

```bash
python main.py --mode batch-workflow-auto --spreadsheet-id "VOTRE_SPREADSHEET_ID"
```

Cette commande exécute **automatiquement** :
1. Audit GSC pour toutes les lignes avec `audit_gsc = AUDITING`
2. Audit SERP pour toutes les lignes avec `audit_serp = AUDITING`
3. Decision pour toutes les lignes avec `audit_gsc = DONE` ET `audit_serp = DONE`
4. Refresh pour toutes les lignes avec une action définie (PARTIAL REFRESH, REFRESH TITLES, FULL REFRESH)

---

### **Options Avancées**

#### Filtrer par Blog

```bash
python main.py --mode batch-workflow-auto \
  --spreadsheet-id "VOTRE_ID" \
  --blog-id enseigna
```

#### Désactiver l'Auto-Refresh (Step 4)

```bash
python main.py --mode batch-workflow-auto \
  --spreadsheet-id "VOTRE_ID" \
  --no-auto-refresh
```

Utile pour :
- Vérifier les décisions avant de lancer les refreshs
- Tester le workflow sur les 3 premières étapes uniquement

#### Mode Verbose

```bash
python main.py --mode batch-workflow-auto \
  --spreadsheet-id "VOTRE_ID" \
  --verbose
```

---

## 📋 Prérequis dans le Google Sheet

### **Configuration Initiale**

Avant de lancer le workflow, assurez-vous que votre Google Sheet `Refreshs_Audit` contient :

| Colonne | Nom | Valeur Requise | Description |
|---------|-----|----------------|-------------|
| A | blog_id | `enseigna`, `moments-yoga`, etc. | Identifiant du blog |
| B | blogpost_url | URL complète | URL de l'article à traiter |
| C | main_keyword | Mot-clé principal | **OBLIGATOIRE** pour audit SERP |
| D | title | Titre actuel | Titre de l'article |
| E | post_type | PARENT / CHILD / STANDALONE | Type d'article (architecture sémantique) |
| F | action_blogpost | (vide) | Sera rempli par Step 3 |
| G | status | (vide) | Sera rempli par Step 4 |
| H | audit_gsc | **AUDITING** | ✅ Trigger Step 1 |
| I | audit_serp | **AUDITING** | ✅ Trigger Step 2 |

### **Exemple de Ligne Prête**

```
A: enseigna
B: https://enseigna.fr/avis-superprof
C: superprof avis
D: Superprof Avis 2025 : Notre Test Complet
E: STANDALONE
F: (vide)
G: (vide)
H: AUDITING
I: AUDITING
```

---

## 🎯 Résultat Attendu

Après exécution, chaque ligne sera complétée :

| Colonnes | Description | Exemple |
|----------|-------------|---------|
| **H** | audit_gsc status | `DONE` |
| **I** | audit_serp status | `DONE` |
| **J-L** | Métriques GSC | `impressions_30d: 1250, clicks_30d: 45, ctr_30d: 3.6` |
| **M** | People Also Ask | `"Superprof gratuit ?, Combien coûte Superprof ?"` |
| **N** | Secondary keywords | `"cours particuliers, tarif professeur, avis élèves"` |
| **F** | action_blogpost | `REFRESH TITLES` |
| **Q-S** | Content metrics | `word_count: 1800, images: 5, internal_links: 12` |
| **T-U** | Cannibalization | `flag: NO, urls: ""` |
| **W** | Index diagnostic | `{"verdict": "PASS", "scenario": "INDEXED", ...}` |
| **G** | status (après refresh) | `TITLES DONE` |
| **O-P** | New titles | `new_h1: "...", new_h2_titles: ["...", "..."]` |

---

## 🐛 Résolution des Problèmes

### **Erreur : "main_keyword is required for SERP analysis"**

**Cause** : La colonne C (main_keyword) est vide pour certaines lignes avec `audit_serp = AUDITING`.

**Solution** :
1. Vérifiez que **toutes** les lignes avec `audit_serp = AUDITING` ont un `main_keyword` en colonne C
2. Remplissez les cellules vides
3. Relancez le workflow

---

### **Colonne W (index_diagnostic) vide**

**Cause** : Quota API GSC URL Inspection dépassé (max 2000 requêtes/jour).

**Solution** :
1. Attendez 24h pour que le quota se réinitialise
2. Ou lancez le workflow sur un sous-ensemble de lignes avec `--blog-id`

---

### **Colonnes Q-U vides**

**Cause** : Le Step 3 (Decision Engine) a échoué ou n'a pas été exécuté.

**Solution** :
1. Vérifiez les logs pour voir les erreurs du Step 3
2. Assurez-vous que les colonnes H et I sont à `DONE` avant le Step 3
3. Relancez le workflow complet

---

## 📈 Performances

| Métrique | Valeur Moyenne |
|----------|----------------|
| Durée Step 1 (GSC) | 2-3s par URL (avec rate limiting) |
| Durée Step 2 (SERP) | 1-2s par URL |
| Durée Step 3 (Decision) | 0.5s par URL |
| Durée Step 4 (Refresh) | Variable (5-30s selon action) |
| **Total pour 10 URLs** | ~5-10 min (selon actions) |

---

## 🔧 Corrections Apportées

### **1. Extraction H2 (Colonne P)**
- ✅ Avant : Réutilisait la valeur existante du sheet
- ✅ Maintenant : Extrait les H2 du contenu refreshed via BeautifulSoup

### **2. Gestion Erreurs SERP**
- ✅ Avant : Message d'erreur générique "main_keyword is required"
- ✅ Maintenant : Affiche l'URL concernée + validation `.strip()`

### **3. Workflow Automatisé**
- ✅ Avant : 4 commandes manuelles à lancer séparément
- ✅ Maintenant : 1 seule commande qui orchestre tout

---

## 📞 Support

Si vous rencontrez des problèmes :

1. Lancez avec `--verbose` pour voir les logs détaillés
2. Vérifiez que toutes les colonnes requises sont remplies
3. Consultez les erreurs retournées dans le résumé final
4. Vérifiez les quotas API (GSC, DataForSEO)

---

**Version** : 2.0
**Dernière mise à jour** : Février 2026
**Auteur** : Claude Opus 4.6
