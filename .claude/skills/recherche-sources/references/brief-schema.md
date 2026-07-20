# Brief de sources — schéma et flux

Référence chargée à la demande depuis `recherche-sources`. Format de sortie de la skill
et façon dont il alimente la génération.

## Schéma

```json
{
  "sujet": "…",
  "sources": [
    {
      "source": "Nom de l'organisme/auteur (ex. INSEE)",
      "url": "https://… (deep-link vers la page précise)",
      "year": 2025,
      "claim": "La donnée/affirmation exacte que cette source appuie"
    }
  ],
  "lacunes": ["Points non couverts, à traiter avec prudence ou sans chiffre"]
}
```

Champ par champ :

- **`sujet`** — le sujet/URL documenté, tel que reçu.
- **`sources[]`** — sources vérifiées, une entrée par (source × claim). Une même source
  peut apparaître deux fois si elle appuie deux claims distinctes.
  - `source` — organisme ou auteur identifiable (pas « une étude »).
  - `url` — page précise portant l'information (deep-link), jamais une homepage.
  - `year` — année **de la donnée** (pas de la consultation), entier. Obligatoire pour
    toute statistique ; sinon la source est écartée (voir `source-quality.md`).
  - `claim` — l'affirmation exacte appuyée, pour que la génération ne cite pas la source
    hors de son propos.
- **`lacunes[]`** — ce qui n'a pas pu être sourcé : la génération traite ces points sans
  chiffre inventé, ou les évite.

## Exemple rempli

```json
{
  "sujet": "Le soutien scolaire au collège en France",
  "sources": [
    {
      "source": "DEPP (Ministère de l'Éducation nationale)",
      "url": "https://www.education.gouv.fr/…/note-depp-2025-soutien-scolaire",
      "year": 2025,
      "claim": "Part des collégiens bénéficiant d'un accompagnement scolaire hors classe"
    },
    {
      "source": "INSEE",
      "url": "https://www.insee.fr/fr/statistiques/…",
      "year": 2024,
      "claim": "Dépense moyenne des ménages en cours particuliers"
    }
  ],
  "lacunes": ["Efficacité comparée présentiel vs en ligne : pas de source primaire datée"]
}
```

## Flux d'injection (état actuel)

Le brief circule **en argument** (conversationnel), pas via un fichier :

1. La skill (invoquée seule ou par l'orchestrateur `refresh`, étape « Recherche
   sources ») produit ce JSON.
2. `refresh` le passe **en argument** au subagent `content-generator`, **à côté** du
   chemin `generation_prompt.txt` (voir `.claude/commands/refresh.md`, étapes 2-3).
3. Le subagent s'en sert pour **le contenu** (citations sourcées, statistiques datées)
   et pour renseigner le champ **`eeat_sources`** de la métadonnée
   (`source`/`url`/`year` — le `claim` n'y va pas, il ne sert qu'au placement in-texte ;
   voir `format-wordpress/SKILL.md`).

> Le brief **ne transite pas** par `generation_prompt.txt` : ce fichier ne contient que
> les données produites par `cw refresh` (GSC/SERP/PAA/intent/assets). Ne pas y chercher
> de slot « sources ».

## Backlog — rendre le flux déterministe

Pour reproduire le brief sans intervention, mirror du précédent PAA : ajouter le champ
au `MinimalRow` (`cli/commands/refresh.py`), le propager dans `audit_data`, puis rendre
une section `### Sources vérifiées` dans `ghostwriter._build_generation_prompt`
(`scripts/ghostwriter/ghostwriter.py`, à côté de la section PAA). Non fait à ce jour.
