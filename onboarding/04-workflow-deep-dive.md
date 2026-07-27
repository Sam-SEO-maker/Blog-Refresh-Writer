# 04 — Le workflow de refresh, en détail

Ce document explique **chaque tâche SEO** qu'exécute un `/refresh`, dans l'ordre,
avec pour chacune : ce qu'elle fait, sur quelles données, et pourquoi elle est
construite ainsi. Pas de code à lire — juste comprendre ce que fait le moteur
entre le moment où vous tapez `/refresh` et le moment où vous récupérez un
article prêt à publier.

Chaque section technique a un encadré replié **« Pour aller plus loin
(technique) »** — à ignorer si vous n'avez pas besoin de savoir quel fichier
Python fait quoi.

---

## Vue d'ensemble

Les étapes d'un refresh sont les suivantes :

```
1     Identification (Sheet) / ingestion de l'URL
1.5   (retiré 2026-07)
2     Audit (GSC, SERP, intention)
  2.1   GSC (performance actuelle)
  2.2   SERP / DataForSEO (concurrence + PAA)
  2.3   Intention de recherche
  2.4   Cannibalisation SEO (GSC + sitemap, tout le site)
2.5   Guide sémantique YTG (enrichissement optionnel, non-bloquant)
3     Décision de stratégie (moteur data-driven)
3.1   Vérification anti-doublon de titre (Notion, périmètre limité, non-bloquant)
3.2   Recherche de sources (brief E-E-A-T)          ← skill, hors STEP du moteur
3.3   Plan éditorial (content_plan.md)               ← skill, hors STEP du moteur
4     Writing : préparation + génération (subagent, Claude Max)
5.1   QC sémantique YTG (SOSEO/DSEO)
5.2   Maillage interne + validation des assets (Golden Rule)
6     Sync : sauvegarde et finalisation
```

Une seule commande déclenche tout ça : `/refresh <url> --site <site-slug> --main-keyword "<mot-clé>"`.
Les étapes 1 à 3.1 sont **déterministes** (aucune IA, juste des calculs et des
appels API) ; l'IA n'intervient qu'à partir de la recherche de sources (3.2)
et de la génération (étape 4).

**Toujours passer `--main-keyword`.** Sans lui, le moteur devine le mot-clé
depuis le slug de l'URL — n'importe quelle coquille ou raccourci dans le slug
part directement dans la requête SERP, et toute l'analyse (PAA, concurrence,
guide YTG) porte alors sur un mot-clé que personne ne recherche vraiment.

---

## 1 — Identification

L'URL à traiter est repérée dans le Google Sheet du site (onglet de suivi :
statut éditorial, action suggérée). C'est le point d'entrée de `/batch` pour
un traitement en masse ; pour un `/refresh` unique, vous fournissez l'URL
directement.

---

## 2 — Audit (GSC, SERP, intention)

`STEP 2` du code (`audit_engine.full_audit()`) fait en un seul appel les
trois lectures détaillées ci-dessous : performance GSC, analyse SERP/PAA, et
détection de l'intention. Elles sont présentées ici en trois sous-étapes
(2.1, 2.2, 2.3) pour la lisibilité, mais s'exécutent comme un seul bloc
dans le moteur — il n'y a pas de séquencement séparé entre elles côté code.

### 2.1 — GSC (performance actuelle)

Avant de toucher au contenu, le moteur regarde comment la page se comporte
**aujourd'hui** dans Google Search Console : clics, impressions, CTR,
position moyenne, et les requêtes qui l'amènent déjà du trafic (fenêtre 12
mois avec repli si peu de données).

Pourquoi : une page qui reçoit 40% de ses clics sur une requête inattendue
mérite un traitement différent d'une page qui ne reçoit rien. Cette lecture
alimente aussi la **résolution du mot-clé principal** s'il n'a pas
été fourni (fallback : GSC → autres sources → slug de l'URL, en dernier recours).

<details>
<summary>Pour aller plus loin (technique)</summary>

`GSCAnalyzer` (module audit). Accès direct pour les sites Superprof via le
MCP `gsc-remote` (auth côté serveur, rien à configurer) ; via service account
pour les sites hors Superprof (Enseigna, futurs clients).
`KeywordResolver` (`scripts/audit/keyword_resolver.py`) fait la résolution
multi-source du mot-clé.
</details>

---

### 2.2 — SERP / DataForSEO (concurrence + PAA)

Le moteur interroge Google (via l'API DataForSEO) sur le mot-clé principal et
récupère le **TOP 20** des résultats organiques, plus tout ce que Google
affiche autour : featured snippet, **People Also Ask** (les questions « Les
internautes demandent aussi »), local pack, résultats vidéo.

Trois choses en ressortent :

- **Le TOP 10 concurrent** — ce qui rank déjà sur ce mot-clé, pour repérer les
  angles qu'ils couvrent et que l'article n'a pas encore (le « gap »).
- **Les questions PAA** — matière première de la FAQ et de sections entières
  de l'article (voir section 3.3).
- **Le format dominant du SERP** — guide pratique, comparatif, définition… Si
  Google affiche majoritairement des comparatifs sur ce mot-clé, un article
  au format « définition » n'a aucune chance de rivaliser, quelle que soit sa
  qualité.

Le volume de recherche du mot-clé est recherché en priorité chez **Ahrefs**,
avec DataForSEO en repli si Ahrefs ne le connaît pas.

Cette étape est **purement mécanique** : extraction de données depuis la
réponse JSON de l'API, aucune génération de texte ni d'IA impliquée.

<details>
<summary>Pour aller plus loin (technique)</summary>

`scripts/audit/serp_analyzer.py::SERPAnalyzer`. Appel API direct (Basic Auth,
pas de MCP) sur `serp/google/organic/live/advanced` (depth 20, `google.fr`).
Découverte/volume du mot-clé via les endpoints DataForSEO Labs
(`ranked_keywords`, `keyword_suggestions`, `keyword_overview`,
`related_keywords`) et `AhrefsClient` pour le volume prioritaire.
`analyze()` orchestre parsing organique → `_parse_serp_features` (snippet,
PAA, local pack, vidéo) → `_extract_paa` → `_analyze_format_distribution`
(regex de détection de format) → détection de notre propre position.
</details>

### Où vont les questions PAA ensuite

Les PAA extraites ici ne restent pas dans un coin : elles sont propagées
automatiquement jusqu'au prompt de génération et jusqu'au plan éditorial, pour
qu'aucune question posée par les internautes ne soit oubliée.

<details>
<summary>Pour aller plus loin (technique)</summary>

Chaîne de propagation (réparée par le commit `add39bf` — cf. mémoire
`project_serp_paa_serialization_bug`) :
`AuditEngine.to_dict()` extrait `people_also_ask` (top 5) et
`secondary_keywords` dans `audit_data` → `RefreshWorkflowResult` porte ces
champs → `orchestrator.py`/`cli/commands/refresh.py` les propagent →
`scripts/ghostwriter/ghostwriter.py` injecte deux sections dédiées
(`### People Also Ask…`, `### Mots-clés secondaires…`) directement dans
`generation_prompt.txt`. En mode batch, `MinimalRow.people_also_ask`
(colonne M du Sheet). Vers le plan : `cli/commands/plan.py::_format_paa_block()`
compose le bloc PAA du `content_plan.md`, et `validate_plan()` vérifie que
chaque PAA est couverte.
</details>

---

### 2.3 — Intention de recherche

À partir du SERP (section 2.2), le moteur détecte l'**intention dominante**
derrière la requête : informationnelle, comparative ou transactionnelle. Cette
intention, combinée au format dominant du SERP, cadre la structure que
l'article devra adopter (guide, comparatif, fiche produit…).

---

### 2.4 — Cannibalisation SEO (GSC + sitemap, tout le site)

C'est **ici** que se fait la vraie détection de cannibalisation du pipeline —
à ne pas confondre avec la vérification anti-doublon de titre Notion de la
section 3.1, qui est un signal complémentaire beaucoup plus limité (voir la
mise en garde dans cette section).

Le moteur prend les **vraies requêtes GSC** de l'URL traitée (celles qui lui
amènent déjà des impressions, au-delà d'un seuil minimal pour ignorer le
bruit) et vérifie, pour chacune, si une **autre URL du même site** (recherchée
dans tout le sitemap, pas seulement les articles récents) ranke aussi dessus.
Si oui, un score de recouvrement est calculé, une sévérité est attribuée
(faible/moyenne/élevée), et une stratégie de résolution est suggérée — par
exemple une redirection 301 vers la page qui performe le mieux plutôt qu'une
réécriture des deux pages en parallèle.

Cette détection porte sur **l'historique complet publié du site** (tout ce
qui est dans le sitemap), pas sur une fenêtre de temps limitée : contrairement
à la vérification Notion (section 3.1), elle ne dépend d'aucune base de
commandes éditoriales et ne peut donc pas manquer un doublon simplement parce
qu'il a été publié il y a plus d'un mois.

<details>
<summary>Pour aller plus loin (technique)</summary>

`scripts/audit/cannibalization.py::CannibalizationDetector`, instancié et
appelé dans `scripts/audit/audit_engine.py` (à l'intérieur du `STEP 2`,
`full_audit()`) — ce n'est donc pas une étape séparée côté code, elle
s'exécute dans le même bloc que GSC/SERP/intention. `detect()` prend les
`keywords_data` GSC de l'URL (ignore les mots-clés avec moins de 50
impressions) et les `sitemap_urls` du site, cherche les URLs concurrentes via
`_find_competing_urls()`, calcule un score de recouvrement
(`_calculate_overlap_score`) et une sévérité (`_calculate_severity`), puis
détermine une stratégie de résolution (`_determine_strategy`, ex.
redirection 301). Résultat exposé dans `audit_dict["cannibalization"]`
(`has_issue`, `requires_action`, `suggested_action`).
</details>

---

## 2.5 — Guide sémantique YTG (enrichissement optionnel)

Dès que le mot-clé principal est connu (fourni ou résolu au STEP 2), le
moteur tente de créer ou réutiliser un **guide YourTextGuru** sur ce
mot-clé : c'est le même mécanisme qui servira au contrôle qualité de fin de
pipeline (voir plus bas, section YTG), mais déclenché ici en amont pour que
les termes du champ sémantique cible et les moyennes SOSEO/DSEO des
concurrents (TOP 3 / TOP 10) soient **disponibles dès la génération**, pas
seulement au contrôle final.

Cette étape est **non-bloquante** : si YTG n'est pas configuré pour le site
ou si l'appel échoue (timeout, quota), le workflow continue simplement avec
les termes statiques de la catégorie éditoriale du blog — aucun refresh n'est
jamais bloqué faute de guide YTG.

<details>
<summary>Pour aller plus loin (technique)</summary>

`scripts/agent/orchestrator.py::process_url`, bloc `STEP 2.5`. Résolution du
mot-clé en repli via `KeywordResolver` si l'audit GSC n'en a pas fourni.
Appel `self._fetch_ytg_guide(main_kw, audit_dict)` → alimente
`audit_dict["ytg_guide_id"]`, `semantic_field_override`,
`ytg_competitor_targets` (top3/top10 SOSEO/DSEO), `ytg_term_colors` —
ces clés sont ensuite injectées dans `generation_prompt.txt` pour que la
génération (STEP 4) écrive directement dans la bonne cible sémantique, sans
attendre le contrôle qualité de fin de pipeline pour le découvrir.
</details>

---

## 3 — Décision de stratégie (moteur data-driven)

Le moteur croise tous les signaux collectés (GSC, SERP, intention, gap
concurrentiel, état de l'article existant) pour décider **quoi faire** de
l'URL — jamais à l'intuition. Résultats possibles :

- Une stratégie de réécriture (`full_refresh`, `semantic_reorientation`,
  `format_adaptation`, `title_optimization`…) → on continue le workflow.
- `NO_ACTION` — l'article est déjà bon, rien à faire.
- `BLOCKED_QUALITY_ISSUES` — un problème empêche le traitement automatique
  (à ne pas confondre avec le verdict `BLOCKED` du QC YTG, section 5.1 :
  celui-ci intervient bien plus tard dans le pipeline, sur le HTML déjà
  généré, pour une raison différente — échec technique de l'outil YTG,
  pas un problème de qualité détecté ici).
- `ERROR` — échec technique (fetch impossible, etc.).
- `REDIRECT_301_SUGGESTED` — la page devrait être redirigée plutôt que
  réécrite.

Dans les 4 derniers cas, `/refresh` s'arrête et rapporte : rien n'est généré.

---

## 3.1 — Vérification anti-doublon de titre (Notion, périmètre limité)

⚠️ **Ce n'est pas la détection de cannibalisation du pipeline** — celle-ci
tourne dès l'étape 2.4, sur GSC + le sitemap complet du site. Cette
vérification-ci est un signal complémentaire, plus étroit : elle regarde
uniquement dans la base Notion des **commandes éditoriales**, qui ne
recense en pratique que les commandes en cours (de l'ordre du mois courant),
pas l'historique complet du site. Un article publié il y a six mois avec un
titre proche ne remontera **jamais** ici — seule la détection GSC/sitemap de
l'étape 2.4 peut le voir, puisqu'elle s'appuie sur ce qui est réellement
indexé et sur le trafic réel, pas sur un journal de commandes.

Avant de lancer la préparation de la génération, le moteur vérifie donc,
dans cette même base Notion, si un article au **titre très proche** n'a pas
déjà été commandé pour ce site récemment — pour éviter qu'une commande en
cours ne fasse doublon avec une autre commande en cours.

Cette vérification est **entièrement non-bloquante** : si Notion n'est pas
configuré pour le site, ou si l'appel échoue, le refresh continue sans
interruption. En cas de correspondance trouvée, elle est simplement
consignée (titre existant, URL, statut) pour information — elle ne bloque
jamais automatiquement la génération.

<details>
<summary>Pour aller plus loin (technique)</summary>

`scripts/agent/orchestrator.py::process_url`, bloc `STEP 3.5a`.
`NotionClient.get_commandes()` + `find_title_match()` sur la base
« commandes » configurée par site (`_get_notion_commandes_db_id`) ; résultat
stocké dans `audit_dict["notion_title_match"]`.
</details>

---

## 3.2 — Recherche de sources (brief E-E-A-T)

**Pourquoi cette étape existe** : sans elle, les statistiques et citations
d'expert de l'article seraient inventées par l'IA au moment de la génération.
Le brief de sources vérifiées est construit **avant** d'écrire, jamais après.

### La règle absolue : la blacklist d'abord

Avant toute recherche web, le moteur charge en mémoire la liste des ~750
domaines interdits (concurrents, agrégateurs, toutes les éditions de
Wikipédia). Le filtrage se fait **a priori** et porte sur la **citation et le
lien**, jamais sur la lecture : un domaine blacklisté n'est jamais gardé dans
un « top N » de sources, jamais ajouté au brief, jamais lié en `href` dans le
HTML — il est écarté dès qu'il apparaît dans une liste de résultats candidats
à citer, pas après coup. En mode batch, cette règle est rechargée en mémoire
à **chaque article**.

**Ce que la blacklist n'interdit pas.** Deux choses restent possibles :

- **Nommer un concurrent dans le texte** d'un article comparatif (« Acadomia
  propose un tarif de X€/h ») : une mention factuelle sans lien n'est pas une
  citation au sens E-E-A-T et n'est pas bloquée. Elle ne prend jamais la
  forme d'un `href`, et n'entre jamais dans `eeat_sources`.
- **Lire une page blacklistée pour l'analyse concurrentielle** — étudier sa
  structure, son angle, ce qu'elle couvre que l'article actuel ne couvre
  pas encore : c'est le même objectif que le scrape du TOP 10 SERP (section
  2.2), en plus poussé. Dépasser une page concurrente mieux positionnée
  commence souvent par la lire. Rien de ce qui est lu ainsi ne peut devenir
  une source citée ou un lien — cette interdiction reste absolue — mais la
  lire pour nourrir le plan éditorial (section 3.3) est permis.

Deux autres exceptions : un lien existant vers un domaine blacklisté est
préservé (Golden Rule — voir section 5.2), et un article de type « avis »
dont le sujet *est* la plateforme concurrente peut la citer/lier légitimement
(elle est alors une source primaire sur elle-même : prix, offre, CGV).

### La recherche en cascade (3 niveaux)

1. **Niveau 1 — l'annuaire du site.** Chaque site peut avoir un annuaire de
   domaines d'autorité validés par un humain, classés par sujet
   (`sites/<site-slug>/sources/authority-map.md`). L'annuaire dit *où*
   chercher (quels domaines), jamais *quelle page précise* — pas d'invention
   d'URL. S'il n'existe pas encore pour un site, on passe directement au
   niveau 2.
2. **Niveau 2 — recherche web ciblée.** Interrogation des domaines identifiés
   au niveau 1 (ou, à défaut d'annuaire, des sources primaires évidentes du
   domaine). Recherche large multi-sources pour un sujet complexe, ou
   vérification ponctuelle (une date, un chiffre) pour un point précis.
   Bonnes pratiques : cibler la page exacte plutôt que la page d'accueil, et
   remonter systématiquement d'un agrégateur (article de presse, Wikipédia) à
   la source primaire qu'il cite — c'est **cette source primaire** qui va
   dans le brief, jamais l'agrégateur.
3. **Niveau 3 — enrichissement de l'annuaire.** Un domaine d'autorité
   confirmé au niveau 2 est proposé pour intégration à l'annuaire du site,
   sous validation humaine. C'est ce qui fait grossir le niveau 1 au fil des
   articles.

### Critères de qualité d'une source

Sources primaires (INSEE, ministères, revues à comité de lecture, organismes
officiels) préférées aux blogs et agrégateurs. Jamais Wikipédia — ce n'est
pas une source d'autorité E-E-A-T, c'est un agrégateur : on cite la source
primaire qu'elle cite elle-même. Une donnée datée doit être récente. Une
source doit être vérifiable (URL qui résout, auteur/organisation
identifiable). Toute source non résolue ou non datée est écartée **avant**
d'entrer dans le brief.

### Ce que produit cette étape

Un brief structuré : le sujet, une liste de sources (chacune avec son URL,
son année, et l'affirmation précise qu'elle appuie), et les lacunes
identifiées (ce qu'on n'a pas réussi à sourcer). Ce brief est transmis
directement au subagent de génération pour nourrir le contenu et le champ de
métadonnées `eeat_sources`.

<details>
<summary>Pour aller plus loin (technique)</summary>

Skill `.claude/skills/source-research/SKILL.md` +
`references/{source-quality,brief-schema,blacklisted-domains}.md`. Le brief
voyage **en argument** du subagent `content-generator`, pas via
`generation_prompt.txt` (contrairement aux PAA) — le SKILL.md note lui-même
que ce câblage différent est une dette à combler pour la reproductibilité.
</details>

---

## 3.3 — Le plan éditorial (`content_plan.md`)

**Pourquoi un plan avant d'écrire** : vérifier la couverture des questions, le
placement des preuves et la hiérarchie des titres se fait en 30 secondes sur
une page de plan. Vérifier la même chose sur 2000 mots d'article déjà généré
coûte cher — et si le plan est mauvais, il faut relancer toute la génération
(et repasser par la boucle de QC sémantique YTG, voir section 5.1). Corriger un
plan coûte quelques lignes ; corriger un article régénéré coûte des jetons et
du temps.

Le squelette est d'abord posé mécaniquement (`plan init`), pré-rempli avec
les signaux déjà collectés (PAA, mot-clé, intention, inventaire des assets) —
puis l'IA **remplit** ce squelette avec le plan proprement dit.

### Méthode de construction du plan

1. **Ancrer sur l'intention** — le format dominant du SERP (section 2.3) dicte le
   squelette (guide pratique, comparatif, définition…), pas un plan
   générique.
2. **Faire correspondre chaque PAA à une section** — chaque question PAA doit
   trouver un H2 ou H3 qui y répond directement en ouverture. Les PAA proches
   sont regroupées sous un même H2. **Aucune PAA orpheline** (non couverte).
3. **Combler le gap concurrentiel** — comparer aux angles du TOP 10 et
   ajouter les sections manquantes qui expliquent pourquoi ces concurrents
   rankent, sans les copier : apporter l'angle en plus.
4. **Répartir les preuves** — les sources et statistiques du brief (section
   5bis) sont distribuées sur plusieurs H2 (jamais toutes dans l'intro), et
   chaque affirmation forte est reliée à une source précise du brief.
5. **Nettoyer la hiérarchie** — appliquer les règles ci-dessous.
6. **Placer les assets** — chaque image/tableau/vidéo/lien à préserver
   (Golden Rule) est rattaché à une section précise.

### Règles de hiérarchie des titres (toujours vraies)

- **Au moins 3 H2** par article — en dessous, le sujet est sous-structuré
  pour l'extraction par les IA génératives.
- **Aucun H2 orphelin** — chaque H2 porte du contenu réel, jamais deux H2
  collés ni un H2 vide servant de simple transition.
- **Aucun H3 orphelin** — sous un H2, soit 0 H3, soit 2 ou plus. Un H3 seul
  est fusionné dans le corps du H2.
- **Seuil de subdivision** — si le contenu prévu d'un H2 dépasse 150 mots,
  il se découpe en 2 à 4 H3.
- **Plafond** — 4 H3 maximum par H2 ; au-delà, on scinde le H2 en deux H2
  distincts.
- **Titre interrogatif → `?`** — un H2/H3 formulé comme une question se
  termine par un point d'interrogation ; un titre déclaratif n'en prend pas.

Ces règles peuvent être resserrées par la skill spécifique d'un site, jamais
assouplies.

### Validation mécanique avant génération

```bash
python3 content_writer.py plan check <url> --site <site-slug>
```

100% déterministe (aucun appel IA) : vérifie la hiérarchie des titres, la
couverture des PAA, le placement des preuves (≥3 sources, ≥2 statistiques).
Verdict `OK` → on génère. Verdict `NEEDS_FIX` → on corrige le plan (pas cher)
avant d'écrire l'article, jamais après.

<details>
<summary>Pour aller plus loin (technique)</summary>

`cli/commands/plan.py` (`plan init`, `plan check`, `_format_paa_block()`,
`validate_plan()`). Skill `.claude/skills/seo-outline/SKILL.md` +
`references/outline-heuristics.md` pour les cas limites de subdivision.
</details>

---

## 4 — Writing : préparation + génération (subagent `content-generator`)

Dans le code, `STEP 4` du moteur ne fait que **préparer le contexte**
(sélection de la stratégie via `StrategySelector`, composition du prompt de
génération) — il ne rédige rien lui-même. La rédaction proprement dite est
déléguée à un subagent dédié, qui tourne sous
l'abonnement Claude Max — **jamais l'API payante**. Il reçoit tout ce qui a
été préparé en amont : le prompt de génération (PAA, intention, SERP,
mots-clés déjà intégrés), le plan validé (il écrit *à partir* du plan,
section par section, sans le réinventer), le brief de sources vérifiées, et
le décompte d'assets avant refresh (pour la Golden Rule).

Le subagent écrit les fichiers directement sur disque — il ne renvoie jamais
de HTML dans le chat.

### Les règles éditoriales appliquées pendant l'écriture

Trois familles de règles cadrent l'écriture, chargées par les skills
transverses `edito-refresh` (le fond) et `format-wordpress` (la forme), plus
la skill propre au site (structure/ton spécifiques) :

**Réponse directe (extraction IA).** Chaque H2 est suivi d'une réponse
directe en 1-2 phrases (40-60 mots) avant tout développement. Idem pour
chaque question de FAQ (50-100 mots). Les moteurs génératifs extraient les
premières phrases de chaque section — c'est elles qui sont citées.

**Preuves : statistiques et citations sourcées.** Au moins 2 statistiques
récentes (2025-2026) au format « [chiffre] + [source] + [date] », au moins 1
citation d'expert avec des identifiants vérifiables (nom, titre,
institution). Jamais une statistique sans date — une IA générative la traite
comme obsolète.

**Sources institutionnelles.** Au moins 3 sources institutionnelles citées
avec un lien. Jamais de lien vers Wikipédia — on cite la source primaire que
Wikipédia agrège elle-même. Pas de bloc « Sources » ni de bio auteur dans le
HTML : géré par le profil WordPress, en dehors du corps de l'article.

**Densité sémantique : en occurrences, jamais en pourcentage.** L'erreur
courante n'est pas d'utiliser trop peu de termes différents, c'est de
répéter les 5-6 mêmes termes trop souvent. La cible est la **couverture**
(largeur du champ sémantique), pas la répétition :

| Élément | Limite |
|---|---|
| Mot-clé principal (exact) | 3-6 occurrences (H1 + intro + 1-2 H2 + conclusion) |
| Termes importants du sujet | 2-5 occurrences chacun, répartis |
| Autres termes du champ sémantique | 1-3 occurrences chacun |
| Espacement | jamais le même terme dans 2 paragraphes consécutifs |

Tout terme apparaissant 3 fois ou plus est remplacé par un synonyme ou une
paraphrase dans au moins 50% de ses occurrences.

La cible SOSEO/DSEO (voir section 5.1) est **variable selon le SERP de chaque
requête**, jamais un seuil fixe uniforme.

**Formats extractibles par l'IA.** Listes à puces pour les énumérations,
tableaux comparatifs pour les synthèses, format Q&R explicite en FAQ (3 à 5
questions PAA par défaut), phrases courtes (15-20 mots).

**Fraîcheur.** Statistiques et dates à jour (sources 2025-2026), sans jamais
changer la date de publication sans modification substantielle du contenu
(pénalisé par Google).

**Structure GEO-ready.** Réponse directe après le H2 → développement sourcé
→ citation d'expert → liste de points. La structure d'ensemble (blocs, ordre,
intro) reste définie par la skill du site, qui prévaut sur ce rappel.

### Les 9 stratégies GEO (Generative Engine Optimization)

Au-delà du SEO classique (être trouvé dans le SERP), l'objectif GEO est
d'être **cité** par les moteurs génératifs (ChatGPT, Perplexity…) comme LA
réponse. Neuf leviers, dont les deux plus efficaces combinés
(**Fluency Optimization + Ajout de statistiques**, +5.5% vs un seul levier
utilisé seul) :

1. Ajout de statistiques récentes et sourcées (+41% de visibilité)
2. Citations d'expert avec identifiants (+28% d'impressions)
3. Optimisation de la fluidité (phrases courtes, sujet-verbe-complément)
4. Structure en réponse directe
5. Listes et tableaux de synthèse
6. Format Q&R explicite en FAQ
7. Preuves d'expertise (E-E-A-T)
8. Apparaître dans des comparatifs tiers (les IA les citent verbatim)
9. Stratégie multi-plateforme (réseaux sociaux, presse, backlinks .edu/.gov)

À proscrire : le bourrage de mots-clés (moins efficace en GEO qu'en SEO
classique), le contenu générique sans sources, les statistiques sans date, un
article sans auteur identifié, et changer la date de publication sans raison
(pénalisé par Google).

### Le cadre E-E-A-T (Experience, Expertise, Authoritativeness, Trust)

Les 4 piliers qui structurent la confiance accordée à un article — Trust est
le plus important : sans lui, les autres signaux ne suffisent pas.

- **Experience** — détails concrets et nuances qu'un praticien seul
  connaîtrait, vocabulaire de terrain, plutôt qu'une description générique.
- **Expertise** — sources académiques, données de moins de 2 ans, vocabulaire
  technique expliqué, études méthodologiquement solides.
- **Authoritativeness** — auteur avec identifiants complets (titre,
  affiliation, publications), citations de sources primaires.
- **Trustworthiness** — méthodologie explicite, dates visibles, sources
  vérifiables avec lien, absence de conflit d'intérêt.

Sujets YMYL (« Your Money or Your Life », impactant la santé, les finances ou
le bien-être du lecteur) exigent un niveau E-E-A-T renforcé — c'est le cas de
l'éducation (sources institutionnelles, données officielles) et du prix/tarif
(transparence, comparaisons objectives).

### Règles de format HTML/WordPress

Balises autorisées : `h2`, `h3`, `p`, `ul`, `ol`, `li`, `strong`, `em`, `a`,
`table`, `img`, `blockquote`. Jamais de wrapper WordPress dans le HTML généré
(`article`, `header`, `div.entry-content`…) — WordPress gère ces éléments
lui-même. Chaque refresh produit deux fichiers : le HTML brut (debug, à
supprimer après génération) et le `.gutenberg.html` (le seul utilisé pour la
publication, blocs `wp:*` prêts à coller dans l'éditeur WP). Accents français
obligatoires, tiret cadratin `—` interdit, ancres de lien sans `<strong>`,
jamais de lien à l'intérieur d'un H2/H3, ponctuation des listes à la
française (virgule en fin d'item, point sur le dernier). Chaque tableau
devient un CSV séparé (max 3 par article), jamais de shortcode dans le HTML.

<details>
<summary>Pour aller plus loin (technique)</summary>

Agent `.claude/agents/content-generator.md`. Règles de fond :
`.claude/skills/edito-refresh/SKILL.md` + `references/{geo-strategies,
eeat-framework,semantic-density}.md`. Règles de forme :
`.claude/skills/format-wordpress/SKILL.md` + `references/typographie-fr.md`.
Le prompt final est composé par `PromptComposer` : stratégie
(`_shared/strategies/`) + `site.md` du site (+ `vs_concurrent.md` pour les
articles versus sur enseigna.fr) — les autres niveaux de composition (base,
catégorie, template) sont inactifs. Règle **Site > Strategy**.
</details>

---

## 5.1 — QC sémantique YTG (YourTextGuru)

Une fois le HTML généré, un contrôle sémantique automatique compare
l'article aux vrais concurrents du SERP, via l'outil externe YourTextGuru.

### Comment ça marche

Un « guide » YTG est créé (ou réutilisé s'il existe déjà pour ce mot-clé) sur
le mot-clé principal : YTG interroge le SERP réel et calcule, à partir des
articles qui rankent, deux scores de référence pour le TOP 3 et pour le TOP
10 :

- **SOSEO** — score de couverture sémantique (a-t-on utilisé les bons termes
  du champ lexical du sujet ?).
- **DSEO** — score de danger de sur-optimisation (répète-t-on trop les mêmes
  termes ?).

L'article généré est ensuite analysé et comparé à ces deux moyennes. La règle
n'est **jamais un seuil fixe** — elle est relative au SERP de la requête :

| Métrique | Règle vs moyenne TOP 3 | Règle vs moyenne TOP 10 |
|---|---|---|
| SOSEO (couverture) | article **>** moyenne | article **>** moyenne |
| DSEO (danger) | article **strictement <** moyenne | article **strictement <** moyenne |

Battre la moyenne suffit, il ne faut pas la pulvériser : un article à 116%
SOSEO / 37% DSEO est inutilisable (sur-optimisation). Dépasser la moyenne
SOSEO de quelques points suffit ; le DSEO doit toujours rester sous les deux
moyennes.

### Le verdict

- **`OPTIMAL`** → SOSEO ≥ cible ET DSEO ≤ cible. L'article passe à l'étape
  suivante (maillage interne).
- **`NEEDS_FIX`** → SOSEO ou DSEO hors cible, **dans un sens ou dans
  l'autre** : sous-optimisation (SOSEO trop bas, des termes du champ
  sémantique manquent) aussi bien que sur-optimisation (DSEO trop haut,
  trop de répétitions). Le rapport liste précisément les termes
  sous-optimisés et sur-optimisés ; le subagent de génération est relancé
  pour corriger le HTML en conséquence — ajouter les termes manquants,
  varier/réduire les termes en excès — (boucle plafonnée à 2-3 itérations),
  puis le QC repasse.
- **`BLOCKED`** → **ce n'est pas un verdict de contenu.** Il ne se déclenche
  jamais sur la base d'un score SOSEO/DSEO trop mauvais — un article très
  sur-optimisé reste en `NEEDS_FIX`, pas `BLOCKED`. `BLOCKED` signale un
  **échec technique en amont de toute analyse** : mot-clé principal
  introuvable, guide YTG introuvable ou non créé, ou appel à l'API YTG en
  échec. Dans ces trois cas, aucun score n'est même calculé — relancer le
  subagent de génération ne changerait rien, puisque le problème n'est pas
  dans le HTML généré mais dans la disponibilité de l'outil ou du mot-clé.
  D'où l'arrêt et l'alerte humaine plutôt qu'une boucle de correction :
  il faut d'abord réparer l'accès à YTG ou fournir le bon mot-clé avant de
  pouvoir relancer un QC qui aura quelque chose à mesurer.

Ce contrôle porte sur le **HTML local avant publication** (le
`.gutenberg.html` généré), jamais sur la page live — le WAF de Superprof
bloque de toute façon l'accès direct aux pages publiées.

<details>
<summary>Pour aller plus loin (technique)</summary>

Deux moteurs distincts existent dans le code :

1. **Moteur API YTG** (celui utilisé par `cw ytg qc`) —
   `scripts/audit/ytg_analyzer.py::YTGAnalyzer` (appels à
   `yourtext.guru/api/v2`) et `scripts/audit/ytg_qc.py::YTGQualityCheck`
   (orchestration : résolution du mot-clé → résolution/création du guide →
   `analyze_content()` → verdict). CLI : `cli/commands/ytg.py::qc()`.
   Correction automatique sur `--fix` : `scripts/audit/ytg_autocorrect.py::YTGAutoCorrector`.
2. **Moteur proxy interne** (garde-fou rapide pendant le pipeline, pas de
   véritable appel API, distinct de `cw ytg qc`) —
   `scripts/audit/semantic_checker.py::SemanticChecker`, utilisé par
   l'orchestrateur et le ghostwriter comme sanity-check local.

Détail du modèle d'occurrences et des plafonds de répétition :
`.claude/skills/edito-refresh/references/semantic-density.md`.
</details>

---

## 5.2 — Maillage interne + validation des assets (Golden Rule)

Une fois le contenu validé, les liens internes sont ajoutés selon la carte de
maillage du site (`linking_maps/`). Chaque site a son propre outil (rotator
Superprof, linker avis↔avis pour Enseigna…) — voir la skill du site pour le
détail.

### La Golden Rule (invariant absolu, tous les sites)

**`assets_after ≥ assets_before`** — un refresh ne réduit **jamais** les
assets d'un article : images, tableaux, vidéos, liens internes, et même les
liens externes (y compris vers des concurrents). On enrichit, on
n'appauvrit jamais. Chaque lien existant est conservé à l'identique (URL et
texte d'ancre), sans qu'aucun nouveau lien ne soit injecté à la place.

---

## 6 — Sync : sauvegarde et finalisation

```bash
python3 content_writer.py finalize <url> --site <site-slug> --html-file <Output HTML>
```

Cette commande déterministe enchaîne : sauvegarde du HTML brut + du
`.gutenberg.html` + des CSV de tableaux → validation des assets (Golden Rule,
restauration des assets manquants si besoin) → QC YTG (section 5.1 ci-dessus)
→ maillage interne (section 5.2, `--apply-linking` pour écrire réellement les
liens, sinon dry-run).

**Ne jamais relancer `finalize` deux fois sur la même URL sans repartir d'un
fichier propre** — cela duplique le contenu du `.gutenberg.html` racine.
Publier depuis le sous-dossier daté, pas depuis la racine.

<details>
<summary>Pour aller plus loin (technique)</summary>

Le `STEP 6` d'`orchestrator.py::process_url` ne fait qu'avancer le tracker de
workflow (`workflow_tracker.advance_step(url, "sync")`) — il ne contient pas
lui-même la logique de sauvegarde/QC/maillage. Cette logique vit dans une
commande CLI séparée, `cli/commands/finalize.py`, appelée après la génération
par le subagent : c'est elle qui orchestre réellement `YTGQualityCheck` et le
linker du site. Les deux sont décrits comme un seul `STEP 6` conceptuel ici
car c'est ainsi que `/refresh` les enchaîne pour l'utilisateur, mais dans le
code ce sont deux fichiers distincts.
</details>

---

## Rapport final

À la fin d'un `/refresh`, on récupère : la stratégie appliquée, les sources
sélectionnées, les chemins de sortie (`sites/<site-slug>/outputs/`), le
verdict YTG, le verdict des assets (avant/après), et les liens ajoutés.
Objectif : une URL en entrée → un contenu prêt à publier + un verdict de
qualité + un maillage à jour, sans reprise manuelle.
