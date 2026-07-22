---
name: seo-outline
description: >-
  Comment construire un bon plan éditorial optimisé pour le SEO/GEO (tous
  sites), AVANT de rédiger. Transforme les signaux data-driven (PAA, user
  intent, top 10 SERP, mot-clé, brief de sources) en un outline H2/H3 traçable
  (content_plan.md) : couverture des questions, placement des preuves, gap
  concurrentiel, hiérarchie de titres saine (≥3 H2, pas d'orphelin, 2-4 H3 par
  H2, `?` sur les questions). Invoquée à l'étape 2bis de /refresh, avant la
  génération. Complète edito-refresh (fond) et format-wordpress (forme).
disable-model-invocation: false
---

# Construire un bon plan pour le SEO (outline éditorial)

Skill de **méthode** : comment passer des signaux collectés (PAA, intent, SERP,
mot-clé, sources) à un **outline traçable** — le `content_plan.md` de l'étape 2bis
de `/refresh` — *avant* de brûler les tokens de rédaction.

Pourquoi un outline séparé de la rédaction :

- **Vérifiable** : la couverture des questions, le placement des sources et la
  structure des titres se contrôlent sur une page, pas sur 2000 mots.
- **Correction bon marché** : si l'outline est mauvais, on corrige l'outline
  (quelques lignes), pas l'article entier re-généré (boucle QC YTG A_CORRIGER
  coûteuse).

> **Frontière avec les autres skills.** Le *fond* (réponse directe, densité,
> sources, GEO) = `edito-refresh`. La *forme* (balises, HTML clean, liens
> interdits dans les headings) = `format-wordpress`. La *structure d'ensemble*
> (blocs, ordre, intro/FAQ) = la skill du site, qui **prime**. Cette skill-ci
> ne redéfinit rien de tout ça : elle organise l'outline.

## Où écrire — le squelette est posé par `plan init`

Ne pas deviner le chemin : lancer d'abord `python3 content_writer.py plan init <url>
--site <site-slug>`. Le CLI crée `content_plan.md` dans le bon `context_dir`, pré-rempli
d'un template + des signaux (PAA, mot-clé, intent, assets) extraits de
`audit_data.json` en commentaires. Cette skill **remplit** ce squelette ; le CLI ne
rédige aucune phrase. Une fois rempli, `plan check` valide (verdict OK / A_CORRIGER).

## Entrées

- Le **squelette `content_plan.md`** posé par `plan init` (chemin + signaux prêts).
- `generation_prompt.txt` : PAA, user intent + format dominant, top 10 SERP,
  mot-clé principal + secondaires (déjà collectés par `cw refresh`).
- Le **brief de sources vérifiées** (`recherche-sources`) : source → claim → url → année.
- `Assets avant` : counts images/tableaux/vidéos/liens à préserver (Règle d'Or).

## Sortie — `content_plan.md`

Une section par bloc, chacune traçable à un signal :

1. **Outline H2/H3** — une ligne par section, avec en regard :
   - la/les **PAA couverte(s)** (chaque PAA doit apparaître au moins une fois),
   - l'**intention** servie (informationnelle / comparative / transactionnelle),
   - l'**angle** (ce que la section apporte).
2. **Placement des preuves** — où vont les **≥ 3 sources institutionnelles** et les
   **≥ 2 statistiques** du brief, rattachées à un H2 précis (jamais « quelque part »).
3. **Gap concurrentiel** — angles présents dans le **top 10 SERP** mais absents de
   l'article (à ajouter) ; angles différenciants propres à préserver.
4. **Assets** — assets existants à **préserver** (Règle d'Or) + assets à **ajouter**,
   par section.

## Méthode (ordre de construction)

1. **Ancrer l'intention** : le format dominant de la SERP dicte le squelette
   (guide « comment », comparatif, définition…). Ne pas plaquer un plan générique.
2. **Mapper les PAA sur des sections** : chaque question PAA → un H2 ou un H3 qui y
   répond en tête (réponse directe, cf. `edito-refresh`). Regrouper les PAA proches
   sous un même H2. Aucune PAA orpheline (non couverte).
3. **Combler le gap** : comparer aux angles du top 10 ; ajouter les sections
   manquantes qui expliquent leur ranking, sans copier — apporter l'angle en plus.
4. **Distribuer les preuves** : répartir sources et stats sur plusieurs H2 (pas
   toutes dans l'intro). Chaque affirmation forte adossée à une source du brief.
5. **Assainir la hiérarchie** : appliquer les invariants ci-dessous.
6. **Placer les assets** : rattacher chaque asset à préserver/ajouter à une section.

## Invariants de hiérarchie des titres (toujours vrais)

La skill du site peut **resserrer** ces bornes, jamais les desserrer.

- **≥ 3 H2** par article. En dessous, sujet sous-structuré pour l'extraction IA.
- **Pas de H2 orphelin** : chaque H2 porte du contenu (jamais deux H2 collés, ni un
  H2 vide servant de simple transition).
- **Pas de H3 orphelin** : sous un H2, soit **0 H3**, soit **≥ 2 H3**. Un unique H3
  se fusionne dans le corps du H2.
- **Seuil de subdivision** : si le contenu prévu d'un H2 dépasse **150 mots** de
  paragraphes, le découper en **2 à 4 H3**. En dessous de 150 mots, pas de H3.
- **Plafond** : **max 4 H3 par H2** ; au-delà, scinder le H2 en deux H2 distincts
  (chacun respectant à son tour la règle des 2-4 H3).
- **Titre interrogatif → `?`** : tout H2/H3 formulé comme une question se termine
  par un point d'interrogation (« Comment réviser le bac ? ») ; un titre déclaratif
  n'en prend pas.
- **Syntaxe ATX correcte, jamais de heading vide** : un H2 s'écrit `## Titre` — le
  `#` en tête de ligne suivi d'un **espace** puis du texte. `##Titre` collé (sans
  espace) n'est PAS un titre pour markdown : il ressortirait en texte brut dans
  WordPress. Et un `## ` sans texte produit un `<h2></h2>` vide qui casse l'éditeur
  Gutenberg : chaque `##`/`###` porte un titre réel, aucun placeholder laissé nu.
- Rappel `format-wordpress` : **pas de lien** dans les H2/H3.

> Cas particuliers de subdivision (H2 à la limite des 150 mots, PAA multiples sous
> un même H2, arbitrage 3 vs 4 H3) : `references/outline-heuristics.md`.

## Checklist avant de passer à la génération

- [ ] ≥ 3 H2, aucun H2 ni H3 orphelin, ≤ 4 H3 par H2.
- [ ] Chaque PAA collectée est couverte par au moins une section.
- [ ] ≥ 3 sources institutionnelles et ≥ 2 stats placées sur des H2 précis.
- [ ] Gap top 10 comblé (sections manquantes ajoutées).
- [ ] Tous les assets à préserver rattachés à une section (Règle d'Or).
- [ ] Titres interrogatifs ponctués `?`.

L'outline validé est transmis au subagent `content-generator`, qui rédige **section
par section à partir de lui** sans réorganiser la structure.
