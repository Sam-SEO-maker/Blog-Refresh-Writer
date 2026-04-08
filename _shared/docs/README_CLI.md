# SRW - Super Refresh Writer CLI

## 📖 Description

CLI unifié pour le workflow de refresh SEO. Remplace les scripts ad-hoc dispersés dans le projet.

## 🚀 Installation

```bash
# Installer les dépendances
pip install click

# Rendre le CLI exécutable (optionnel)
chmod +x srw.py
```

## 📋 Commandes Disponibles

### 🔄 Refresh

Refresh une URL unique avec workflow complet.

```bash
# Refresh simple
srw refresh https://enseigna.fr/article --blog enseigna

# Avec stratégie forcée
srw refresh https://enseigna.fr/article --blog enseigna --strategy FULL_REFRESH

# Avec mot-clé spécifique (force analyse SERP)
srw refresh https://enseigna.fr/article --blog enseigna --keyword "parcoursup"

# Mode debug (affiche traceback complet)
srw refresh https://enseigna.fr/article --blog enseigna --debug
```

**Stratégies disponibles** :
- `TITLE_OPTIMIZATION` : Optimisation titre/meta uniquement
- `PARTIAL_REFRESH` : Refresh partiel (stats, données)
- `FULL_REFRESH` : Refresh complet (réécriture)
- `SEMANTIC_REORIENTATION` : Réorientation sémantique
- `FORMAT_ADAPTATION` : Adaptation format SERP
- `EEAT_REWRITE` : Refonte E-E-A-T

---

### 🚀 Workflow

Workflow complet avec mise à jour spreadsheet.

```bash
# Workflow complet pour une URL
srw workflow run https://enseigna.fr/article --blog enseigna

# Avec spreadsheet ID
srw workflow run https://enseigna.fr/article --blog enseigna --spreadsheet-id "1ABC..."

# Traiter une ligne spécifique du spreadsheet
srw workflow run https://enseigna.fr/article --blog enseigna --row 3
```

**Équivalent à** : `run_workflow_parcoursup.py`

---

### 🔍 Audit

Différents types d'audits.

#### Audit Éditorial

Quality Gate : score < 4.0/10 bloque le refresh.

```bash
srw audit editorial https://enseigna.fr/article --blog enseigna
```

**Critères** :
- Truth Score (40%)
- E-E-A-T Score (30%)
- Freshness Score (20%)
- Genericness Score (10%)

#### Audit Cannibalization

Détecte si des H2 cannibalisent les H1 des siblings.

```bash
srw audit cannibalization https://enseigna.fr/article --spreadsheet-id "1ABC..."
```

**Seuil** : Similarity ≥ 0.75 = HIGH risk

#### Audit SERP

Analyse SERP (PAA, secondary keywords).

```bash
# Avec keyword explicite
srw audit serp https://enseigna.fr/article --keyword "parcoursup"

# Sans keyword (extrait du title)
srw audit serp https://enseigna.fr/article
```

---

### 🔗 Cocons Sémantiques

Gestion des cocons PARENT-CHILD.

#### Identifier les Cocons

Analyse les relations H1 CHILD = H2 PARENT.

```bash
# Tous les formats (JSON, TXT, CSV)
srw cocon identify --spreadsheet-id "1ABC..."

# Format spécifique
srw cocon identify --spreadsheet-id "1ABC..." --output json
srw cocon identify --spreadsheet-id "1ABC..." --output txt
srw cocon identify --spreadsheet-id "1ABC..." --output csv
```

**Équivalent à** : `identify_cocons.py`

**Pré-requis** : Exécuter d'abord :
```bash
srw debug extract-structures --spreadsheet-id "1ABC..."
```

#### Valider les Cocons

Vérifie que les liens PARENT-CHILD sont présents.

```bash
srw cocon validate https://enseigna.fr/article --spreadsheet-id "1ABC..."
```

---

### 📦 Batch

Traitement batch depuis Google Sheets.

#### Batch Audit GSC

Récupère données GSC pour toutes les URLs en attente.

```bash
# Tous les blogs
srw batch audit-gsc --spreadsheet-id "1ABC..."

# Blog spécifique
srw batch audit-gsc --spreadsheet-id "1ABC..." --blog enseigna

# Avec limite
srw batch audit-gsc --spreadsheet-id "1ABC..." --limit 10
```

#### Batch Audit SERP

Récupère PAA et secondary keywords.

```bash
srw batch audit-serp --spreadsheet-id "1ABC..."
srw batch audit-serp --spreadsheet-id "1ABC..." --blog enseigna
```

#### Batch Decision

Prend des décisions de stratégie pour toutes les URLs auditées.

```bash
srw batch decision --spreadsheet-id "1ABC..."
srw batch decision --spreadsheet-id "1ABC..." --blog enseigna
```

**Output** :
- NO_ACTION
- PARTIAL_REFRESH
- REFRESH_TITLES
- FULL_REFRESH

#### Batch Refresh

Génère le contenu pour toutes les URLs avec l'action spécifiée.

```bash
srw batch refresh --spreadsheet-id "1ABC..." --action FULL_REFRESH
srw batch refresh --spreadsheet-id "1ABC..." --action PARTIAL_REFRESH --blog enseigna
```

**Actions** :
- `PARTIAL_REFRESH`
- `REFRESH_TITLES`
- `FULL_REFRESH`

#### Batch Workflow Auto

Workflow automatisé complet : GSC → SERP → Decision → Refresh.

```bash
# Avec auto-refresh
srw batch workflow-auto --spreadsheet-id "1ABC..."

# Sans auto-refresh (decision seulement)
srw batch workflow-auto --spreadsheet-id "1ABC..." --no-auto-refresh

# Blog spécifique
srw batch workflow-auto --spreadsheet-id "1ABC..." --blog enseigna
```

---

### 📤 Indexation

Gestion de l'indexation Google.

#### Demande Indexation

Soumet les URLs avec status "CONTENT DONE" à l'API Google Indexing.

```bash
srw indexing request --blog enseigna --spreadsheet-id "1ABC..."
```

#### Scan Indexation

Vérifie l'état d'indexation via GSC API.

```bash
srw indexing scan --blog enseigna
srw indexing scan --blog enseigna --limit 100
```

#### Diagnostic Bulk

Exécute le diagnostic bulk d'indexation.

```bash
srw indexing bulk-diagnostic --blog enseigna --spreadsheet-id "1ABC..."
```

---

### 🐛 Debug

Utilitaires de debug.

#### Debug Workflow

Exécute le workflow avec traceback complet.

```bash
srw debug workflow https://enseigna.fr/article --blog enseigna
srw debug workflow https://enseigna.fr/article --blog enseigna --strategy FULL_REFRESH
```

**Équivalent à** : `debug_workflow.py`

#### Afficher Config

Vérifie les configurations chargées.

```bash
# Résumé
srw debug config

# Blog spécifique
srw debug config --blog enseigna

# Tous les blogs
srw debug config --show-all
```

#### Extraire Structures

Extrait les structures H1/H2 de toutes les URLs.

```bash
srw debug extract-structures --spreadsheet-id "1ABC..."
```

**Output** : `outputs/articles_structure_YYYYMMDD_HHMMSS.json`

Requis pour `srw cocon identify`.

---

### 🧠 YourTextGuru (YTG)

Guides sémantiques basés sur les vrais scores concurrents SOSEO/DSEO.

#### Créer un guide

```bash
srw ytg create-guide --keyword "bienfaits yoga"
srw ytg create-guide --keyword "musculation dos" --lang fr --country fr
```

**Output** : guide_id + scores TOP 3/TOP 10 + termes colorés (bleu/orange/rouge/vert).

#### Vérifier un guide existant

```bash
srw ytg check-guide --guide-id ABC123
```

#### Pré-fetch batch (recommandé avant workflow)

Crée les guides pour toutes les URLs avec `main_keyword` mais sans `ytg_guide_id` en cache.
À lancer **avant** `srw batch audit-serp` pour que le STEP 2.5 soit instantané.

```bash
srw ytg batch-prefetch --spreadsheet-id "1ABC..."
srw ytg batch-prefetch --spreadsheet-id "1ABC..." --blog moments-yoga
```

#### Analyser un HTML contre un guide

```bash
srw ytg analyze --guide-id ABC123 --html-file _shared/context/.../refreshed.html
```

**Output** : SOSEO et DSEO obtenus pour notre contenu + termes sous-optimisés / en surdose.

**Credentials** :
```env
YTG_API_KEY=ta_cle_ytg
```

**Comportement dans le workflow** : Le STEP 2.5 injecte automatiquement les termes YTG dans `semantic_field_override` (remplace les termes statiques de catégorie) et calibre les seuils SOSEO/DSEO du SemanticChecker sur les vraies données concurrentes.

---

### 💡 Notion

Intégration avec les bases Notion (commandes d'articles, sujets à traiter).

#### Synchroniser les commandes

```bash
srw notion sync --blog moments-yoga --db-id "abc123def456..."
```

#### Vérifier un titre (anti-cannibalisation)

```bash
srw notion check-title --blog moments-yoga --title "Les bienfaits du yoga pour la santé"
srw notion check-title --blog moments-yoga --title "..." --threshold 0.80
```

**Seuil par défaut** : 0.85 (Jaccard sur les mots). Descendre à 0.75 pour plus de sensibilité.

#### Lister les sujets à traiter

```bash
srw notion list-sujets --db-id "abc123..."
srw notion list-sujets --db-id "abc123..." --blog coachsportlyon
```

#### Créer un nouveau sujet

```bash
srw notion create-sujet --blog moments-yoga --title "Yoga pour les seniors" \
  --db-id "abc123..." --category wellness --priority high
```

**Credentials** :
```env
NOTION_TOKEN=secret_votre_token_integration
```

**DB IDs** : À renseigner dans `_shared/config/sites.json` → `notion_commandes_db_id` et `notion_sujets_db_id` pour chaque blog.

**Comportement dans le workflow** : Le STEP 3.5a vérifie automatiquement si le titre de l'article en cours correspond à un article déjà commandé dans Notion (anti-cannibalisation par titre). Non-bloquant.

---

## 🗂️ Architecture

```
srw.py (point d'entrée)
cli/
  commands/
    ├── refresh.py      # Refresh URL unique
    ├── workflow.py     # Workflow complet
    ├── audit.py        # Audits (editorial, cannibalization, serp)
    ├── cocon.py        # Cocons sémantiques
    ├── batch.py        # Traitement batch
    ├── indexing.py     # Indexation Google
    ├── debug.py        # Debug utilities
    ├── ytg.py          # Guides sémantiques YourTextGuru
    └── notion_cmd.py   # Intégration Notion
```

---

## 🔥 Migration des Scripts Ad-Hoc

| Script Ancien | Commande CLI |
|---------------|--------------|
| `debug_workflow.py` | `srw debug workflow <url> --blog <ID>` |
| `identify_cocons.py` | `srw cocon identify --spreadsheet-id <ID>` |
| `run_workflow_parcoursup.py` | `srw workflow run <url> --blog <ID>` |
| `scripts/tests/fetch_child_h1s.py` | `srw debug extract-structures --spreadsheet-id <ID>` |
| `scripts/indexing/bulk_index_diagnostic.py` | `srw indexing bulk-diagnostic --blog <ID> --spreadsheet-id <ID>` |

---

## 📊 Exemples d'Usage

### Refresh Simple

```bash
# Refresh une URL avec audit complet
srw refresh https://enseigna.fr/avis-superprof --blog enseigna
```

### Workflow Complet (Row-based)

```bash
# Traiter la ligne 3 du spreadsheet
python main.py --mode batch-workflow-auto --spreadsheet-id "1ABC..." --row 3
```

### Cocons Sémantiques

```bash
# 1. Extraire structures
srw debug extract-structures --spreadsheet-id "1ABC..."

# 2. Identifier cocons
srw cocon identify --spreadsheet-id "1ABC..."

# 3. Vérifier cannibalization
srw audit cannibalization https://enseigna.fr/article --spreadsheet-id "1ABC..."
```

### Batch Workflow Automatisé

```bash
# Workflow complet automatisé pour blog enseigna
srw batch workflow-auto --spreadsheet-id "1ABC..." --blog enseigna
```

---

## ⚙️ Configuration

### Variables d'Environnement

Créer `.env` à la racine :

```env
SPREADSHEET_ID=1F99FtN8fWQlQm0ZTJphBRz_c64iDs2DvohyHyM2Tk1M
ANTHROPIC_API_KEY=sk-ant-...
DATAFORSEO_LOGIN=...
DATAFORSEO_PASSWORD=...

# YourTextGuru (guides sémantiques)
YTG_API_KEY=ta_cle_ytg

# Notion (commandes + sujets)
NOTION_TOKEN=secret_votre_token_integration
```

### Google Service Account

Credentials : `C:/Users/samue/.credentials/google/service_account.json`

### DataforSEO Credentials

Credentials : `C:/Users/samue/.credentials/dataforseo/credentials.json`

---

## 🆘 Aide

```bash
# Aide générale
srw --help

# Aide commande spécifique
srw refresh --help
srw batch --help
srw batch audit-gsc --help
```

---

## 🧹 Nettoyage

Scripts obsolètes supprimés après migration CLI :
- ✅ `debug_workflow.py`
- ✅ `identify_cocons.py`
- ⚠️ `main.py` (conservé comme fallback legacy)

---

## 📝 Notes

- **MCP Client** : Démarre automatiquement pour analyse SERP/GSC
- **Rate Limiting** : Respect des limites API (GSC, DataforSEO)
- **Assets** : Préservation automatique (images, tableaux, vidéos, liens)
- **Quality Gate** : Audit éditorial bloque si score < 4.0/10
- **Cannibalization** : Détection automatique (seuil 0.75)
- **Logs** : Affichés en temps réel, fichiers dans `data/logs/`
- **YTG** : Guide créé en STEP 2.5, `ytg_guide_id` caché dans `audit_data.json` (pas de recréation sur re-run)
- **Notion** : Vérification titre en STEP 3.5a, non-bloquant si token absent

---

**Version** : 2.1.0
**Date** : Mars 2026
**Agent** : Claude Sonnet 4.6
