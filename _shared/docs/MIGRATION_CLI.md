# Migration vers CLI SRW

## ✅ Changements

### Scripts supprimés

Les scripts suivants ont été **supprimés** et remplacés par des commandes CLI :

| Script supprimé | Commande CLI équivalente |
|----------------|--------------------------|
| `debug_workflow.py` | `python srw.py debug workflow <url> --blog <ID>` |
| `identify_cocons.py` | `python srw.py cocon identify --spreadsheet-id <ID>` |

### Scripts conservés

Les scripts suivants sont **conservés** pour compatibilité :

- `main.py` : Conservé comme fallback legacy (utilisé par certains workflows existants)
- `workflows/run_workflow_parcoursup.py` : Conservé (peut être migré ultérieurement)

### Nouveaux fichiers

- `srw.py` : Point d'entrée CLI principal
- `cli/commands/*.py` : Modules de commandes (refresh, workflow, audit, cocon, batch, indexing, debug)
- `_shared/config/sites.py` : Wrapper Python pour charger sites.json (exposé SITE_CONFIGS)
- `README_CLI.md` : Documentation complète du CLI
- `MIGRATION_CLI.md` : Ce fichier

### Modifications

- `requirements.txt` : Ajout de `click>=8.1.0`
- `_shared/config/sites.json` : Correction `registre: "tutoiement"` → `"vouvoiement"` pour moments-yoga, mymusicteacher, coachsportlyon

---

## 🚀 Utilisation du CLI

### Installation

```bash
# Installer Click
pip install click

# Tester le CLI
python srw.py --help
```

### Exemples de migration

#### Avant (scripts ad-hoc)

```bash
# Debug workflow
python debug_workflow.py

# Identify cocons
python identify_cocons.py

# Run workflow
cd workflows && python run_workflow_parcoursup.py
```

#### Après (CLI unifié)

```bash
# Debug workflow
python srw.py debug workflow https://enseigna.fr/article --blog enseigna

# Identify cocons
python srw.py cocon identify --spreadsheet-id "1ABC..."

# Run workflow
python srw.py workflow run https://enseigna.fr/article --blog enseigna
```

---

## 📋 Commandes principales

### Refresh simple

```bash
python srw.py refresh https://enseigna.fr/article --blog enseigna
```

### Workflow complet

```bash
python srw.py workflow run https://enseigna.fr/article --blog enseigna --spreadsheet-id "1ABC..."
```

### Audit éditorial

```bash
python srw.py audit editorial https://enseigna.fr/article --blog enseigna
```

### Cocons sémantiques

```bash
# 1. Extraire structures
python srw.py debug extract-structures --spreadsheet-id "1ABC..."

# 2. Identifier cocons
python srw.py cocon identify --spreadsheet-id "1ABC..."

# 3. Valider
python srw.py cocon validate https://enseigna.fr/article --spreadsheet-id "1ABC..."
```

### Batch operations

```bash
# Workflow automatisé complet
python srw.py batch workflow-auto --spreadsheet-id "1ABC..." --blog enseigna

# Audit GSC batch
python srw.py batch audit-gsc --spreadsheet-id "1ABC..." --blog enseigna

# Refresh batch
python srw.py batch refresh --spreadsheet-id "1ABC..." --action FULL_REFRESH --blog enseigna
```

---

## 🔍 Aide

```bash
# Aide générale
python srw.py --help

# Aide commande spécifique
python srw.py refresh --help
python srw.py batch --help
python srw.py batch audit-gsc --help
```

---

## ⚠️ Points d'attention

### 1. main.py conservé

Le fichier `main.py` est conservé car il est potentiellement utilisé par :
- Workflows automatisés existants
- Scripts externes
- Cron jobs

**Migration future** : À terme, tous les usages de `main.py` devront migrer vers `srw.py`.

### 2. Spreadsheet ID

Beaucoup de commandes requièrent `--spreadsheet-id`. Vous pouvez :
- Le passer en CLI : `--spreadsheet-id "1ABC..."`
- Le définir dans `.env` : `SPREADSHEET_ID=1ABC...`
- Le configurer par blog dans `_shared/config/sites.json`

### 3. Blog ID obligatoire

Pour toutes les commandes de refresh/audit, `--blog <ID>` est obligatoire.

Blogs valides :
- `enseigna`
- `cours-particuliers`
- `educationetdevenir`
- `moments-yoga`
- `mymusicteacher`
- `coachsportlyon`

### 4. MCP Client

Le MCP Client démarre automatiquement pour les commandes nécessitant DataforSEO/GSC :
- `srw refresh`
- `srw workflow run`
- `srw batch audit-gsc`
- `srw batch audit-serp`
- `srw batch refresh`

Si credentials manquants, le workflow continue sans analyse SERP externe (warning affiché).

---

## 📚 Documentation

Consultez `README_CLI.md` pour la documentation complète avec tous les exemples et options.

---

**Version** : 2.0.0
**Date** : Février 2026
