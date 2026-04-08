# Module Détection Désindexation GSC

Ce module permet d'identifier les pages potentiellement désindexées et les problèmes de cannibalisation pour prioriser les actions de réécriture E-E-A-T.

---

## Méthodes de Détection

### Méthode 1 : Comparaison Sitemap vs GSC

**Principe** : Une URL présente dans le sitemap mais avec 0 impressions sur 90 jours est potentiellement désindexée.

**Processus :**
1. Récupérer toutes les URLs du sitemap
2. Récupérer les données GSC (90 derniers jours)
3. Identifier les URLs avec 0 impressions
4. Exclure les URLs récentes (< 30 jours)

**Outil MCP** :
```
mcp__google-search-console__search_analytics
- siteUrl: https://[domain]/
- startDate: -90 jours
- endDate: aujourd'hui
- dimensions: "page"
- rowLimit: 5000
```

**Interprétation :**
| Impressions 90j | Statut probable |
|-----------------|-----------------|
| 0 | Potentiellement désindexé |
| 1-10 | Faible visibilité |
| 10-100 | Visibilité limitée |
| > 100 | Indexé et visible |

### Méthode 2 : Inspection d'URL Directe

**Outil MCP** :
```
mcp__google-search-console__index_inspect
- siteUrl: https://[domain]/
- inspectionUrl: [URL complète]
```

**Statuts possibles :**
| Verdict | Signification | Action |
|---------|---------------|--------|
| PASS | Indexé et valide | Aucune |
| NEUTRAL | Peut être indexé | Vérifier |
| FAIL | Non indexé | Investiguer |

**Détails à vérifier :**
- `indexingState` : INDEXED, NOT_INDEXED, SUBMITTED_AND_INDEXED
- `pageFetchState` : SUCCESSFUL, FAILED, REDIRECT
- `robotsTxtState` : ALLOWED, DISALLOWED
- `crawledAs` : MOBILE, DESKTOP

### Méthode 3 : Analyse de Chute de Performance

**Signaux d'alerte :**
- Chute soudaine à 0 clics/impressions
- Perte > 80% du trafic en 30 jours
- Disparition complète de requêtes auparavant performantes

**Processus :**
1. Comparer période actuelle vs période précédente
2. Identifier URLs avec variation négative > 80%
3. Croiser avec les dates de mises à jour Google

---

## Détection de Cannibalisation

### Définition
Cannibalisation SEO : Plusieurs pages du même site se disputent le même mot-clé, diluant l'autorité.

### Méthode de Détection

**Outil MCP** :
```
mcp__google-search-console__search_analytics
- dimensions: "query,page"
- rowLimit: 5000
```

**Analyse** :
```
Pour chaque requête:
  → Compter le nombre de pages distinctes classées
  → Si 2+ pages pour même requête → CANNIBALIZATION
```

### Score de Sévérité

| Critère | Sévérité |
|---------|----------|
| 2 pages en top 10 | HAUTE |
| 2 pages en top 20 | MOYENNE |
| 2+ pages, intentions différentes | BASSE |
| Pages avec positions > 50 | TRÈS BASSE |

### Stratégies de Résolution

| Stratégie | Quand l'utiliser |
|-----------|------------------|
| **Merge** | Contenus similaires, fusionner le plus faible dans le plus fort |
| **Différencier** | Contenus proches, modifier les angles/intentions |
| **Redirect 301** | Page faible → page forte |
| **Noindex** | Page secondaire à exclure de l'index |
| **Canonical** | Indiquer la page préférée |

---

## Déclencheurs Réécriture E-E-A-T

### Signaux Prioritaires

| Signal | Poids | Action |
|--------|-------|--------|
| Désindexé après algo update | 5 | Réécriture complète E-E-A-T |
| Chute trafic > 50% / 3 mois | 4 | Audit + refresh profond |
| Position moyenne > 50 malgré impressions | 3 | Optimisation contenu |
| Contenu < 1000 mots sur YMYL | 4 | Enrichissement obligatoire |
| Aucune source citée | 3 | Ajouter références |
| Pas de date de mise à jour | 2 | Actualiser + dater |

### Formule de Priorité Refresh

```
Priority = (Previous_Traffic × 0.4) + (Keyword_Volume × 0.3) + (EEAT_Gap × 0.3)

Où:
- Previous_Traffic: Clics moyens avant chute (0-100 normalisé)
- Keyword_Volume: Volume du mot-clé principal (0-100 normalisé)
- EEAT_Gap: Score de lacunes E-E-A-T (0-100)
```

### Critères YMYL (Your Money Your Life)

Pages nécessitant E-E-A-T renforcé :
- **Santé** : yoga thérapeutique, bien-être mental
- **Éducation** : orientation, reconversion professionnelle
- **Finance** : tarifs, investissement formation
- **Sécurité** : consignes sécurité sport, précautions yoga

---

## Output du Module

### Format JSON Analyse Désindexation

```json
{
  "analysis_date": "2026-02-03",
  "site_id": "moments-yoga",
  "deindexed_pages": [
    {
      "url": "https://moments-yoga.fr/yoga-seniors-exercices/",
      "last_seen_date": "2025-09-15",
      "previous_clicks": 145,
      "previous_impressions": 2300,
      "potential_cause": "thin_content",
      "word_count_estimated": 650,
      "recovery_priority": 4,
      "recommended_action": "Enrichir contenu à 1500+ mots, ajouter sources E-E-A-T"
    }
  ],
  "cannibalization_issues": [
    {
      "query": "cours yoga débutant",
      "severity": "HIGH",
      "pages": [
        {
          "url": "https://moments-yoga.fr/debuter-yoga/",
          "position": 8,
          "clicks": 45,
          "impressions": 890
        },
        {
          "url": "https://moments-yoga.fr/cours-yoga-debutant/",
          "position": 12,
          "clicks": 12,
          "impressions": 340
        }
      ],
      "recommended_action": "MERGE: Fusionner contenu de /cours-yoga-debutant/ dans /debuter-yoga/, redirect 301"
    }
  ],
  "eeat_rewrite_candidates": [
    {
      "url": "https://moments-yoga.fr/bienfaits-yoga/",
      "priority": 5,
      "issues": [
        "Aucune source citée",
        "Pas de date de mise à jour",
        "Contenu générique sans expertise démontrée"
      ],
      "recommended_actions": [
        "Ajouter 3+ statistiques sourcées (INSEE, études)",
        "Citer 2+ experts (médecins, professeurs spécialisés)",
        "Ajouter section méthodologie/expérience",
        "Dater le contenu avec date de révision"
      ]
    }
  ]
}
```

---

## Commandes Rapides

```bash
# Pages potentiellement désindexées
/deindexed moments-yoga

# Détecter cannibalisation
/cannibalization moments-yoga

# Candidats réécriture E-E-A-T
/eeat-audit moments-yoga

# Inspection URL spécifique
/inspect moments-yoga https://moments-yoga.fr/page/
```

---

## Intégration avec Index Inspection API

### Workflow Automatisé

```
1. Lister URLs sitemap avec 0 impressions (90j)
2. Pour chaque URL suspecte:
   → mcp__google-search-console__index_inspect
   → Récupérer verdict, indexingState, issues
3. Classifier:
   - NOT_INDEXED + quality issue → Réécriture E-E-A-T
   - NOT_INDEXED + robots blocked → Fix technique
   - NOT_INDEXED + redirect → Vérifier chaîne redirects
4. Prioriser selon formule Priority
5. Générer rapport actionnable
```

### Fréquence Recommandée

| Action | Fréquence |
|--------|-----------|
| Scan désindexation | Hebdomadaire |
| Analyse cannibalisation | Mensuelle |
| Audit E-E-A-T complet | Trimestriel |
| Post-update Google | Sous 7 jours |

---

*Module Deindexation Detector v1.0 - Février 2026*
