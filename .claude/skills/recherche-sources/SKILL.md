---
name: recherche-sources
description: >-
  Documente un sujet ou une URL avec des sources vérifiées pour nourrir le brief
  E-E-A-T avant génération. Recherche en cascade : bibliothèque curée par matière
  d'abord, puis complément web (deep-research / WebSearch / WebFetch) qui enrichit
  la bibliothèque. Sources réelles et vérifiées, jamais inventées. Invocable seule
  ou appelée par l'orchestrateur refresh. Lecture + écriture biblio.
disable-model-invocation: false
---

# Recherche de sources — brief E-E-A-T

Constitue un socle de **sources vérifiées** pour un sujet/URL, en amont de la
génération. Objectif : nourrir le E-E-A-T avec des références réelles (académiques,
institutionnelles, données chiffrées récentes), **jamais fabriquées**. Ce fichier
porte la **méthode** (transverse, tous tenants) ; le détail vit dans `references/`
(à lire au besoin) :

- `references/source-quality.md`, grille de qualité par type de source + exemples ✅/❌.
- `references/brief-schema.md`, schéma JSON complet du brief + exemple + flux d'injection.
- `references/blacklisted-domains.md`, liste canonique des ~750 domaines interdits
  (concurrents, agrégateurs, tous les Wikipédia) + règle des sous-domaines,
  exceptions (Règle d'Or, article avis dont le sujet EST la plateforme) et substituts.

L'**annuaire** des domaines d'autorité (donnée, par tenant) vit côté tenant, ex.
`tenants/superprof-ressources/sources/authority-map.md` : la skill le consomme au
tier 1, elle ne le remplace pas.

> **Statut : chantier en cours.** Le socle se construit « par le haut » (un annuaire
> matière → autorités par tenant, cf. tier 1) puis s'enrichit article par article
> (tier 3, l'agent propose → l'humain valide). Sans annuaire pour un tenant donné, la
> skill opère en mode « web seul » (tier 2-3) et amorce l'annuaire au passage.

## Étape 0 — Charger la blacklist (obligatoire, AVANT toute recherche)

**Lire `references/blacklisted-domains.md` en entier avant le moindre WebSearch,
WebFetch ou appel deep-research.** Garder la liste en mémoire de travail pour toute
la session et l'appliquer **a priori** :

- Un domaine blacklisté n'est **jamais fetché** ni retenu comme candidat — il est
  écarté dès la lecture de la SERP ou des résultats de recherche, pas après coup.
- Ne jamais empaqueter un « top N » de résultats sans l'avoir d'abord passé au
  crible de la blacklist : le tri se fait **avant** la curation, pas après.
- En **batch / multi-articles** : re-vérifier la blacklist au début de **chaque
  article** (relire le fichier ou re-résumer ses catégories) — la contrainte ne
  doit jamais sortir de la mémoire de travail entre deux itérations.

Les deux exceptions (Règle d'Or sur l'existant, article avis dont le sujet EST la
plateforme) sont définies dans `references/blacklisted-domains.md` et prévalent.

## Recherche en cascade (3 tiers)

### Tier 1 — Annuaire des domaines d'autorité (prioritaire)
Piocher d'abord dans `tenants/{tenant}/sources/` : l'**annuaire** validé par un
humain, réutilisable d'un article à l'autre. Pour `superprof-ressources`,
`authority-map.md` donne les domaines d'autorité **par matière**. Démarche :

1. Identifier la **matière** de l'article (histoire, maths, SES…).
2. Lire la ligne correspondante de l'annuaire → domaines d'autorité prioritaires,
   types de sources à viser, pièges à éviter.
3. Cibler ces domaines au tier 2.

> ⚠️ L'annuaire dit **où** chercher (domaines), jamais **quelle page exacte** : ne
> pas inventer d'URL de page. Si le tenant n'a pas encore de dossier `sources/`,
> passer directement au tier 2 sans inventer de chemin ni de contenu.

### Tier 2 — Recherche web ciblée (résolution effective)
Interroger les domaines retenus au tier 1 (ou, à défaut d'annuaire, les sources
primaires du champ). Choisir l'outil selon le besoin :
- **`deep-research`** (skill) pour un sujet large nécessitant vérification
  multi-source et rapport cité.
- **`WebSearch` / `WebFetch`** pour des vérifications ponctuelles (une stat, une
  date, une source primaire précise).

Bonnes pratiques de requête :
- **Blacklist d'abord** (étape 0 déjà faite) : un résultat SERP/WebSearch appartenant
  à un domaine blacklisté est **ignoré sans être fetché** ; chercher immédiatement
  une alternative non blacklistée.
- **Restreindre au domaine d'autorité** de l'annuaire (`site:insee.fr`,
  `site:hal.science`) plutôt qu'une recherche ouverte.
- **Cibler la page précise** (deep-link) qui porte l'information, jamais la homepage.
- **Remonter d'un agrégateur à la source primaire** : d'un article de presse ou de
  Wikipédia, aller à l'étude / au texte officiel cité, et retenir **celui-ci**.
- **Écarter d'emblée** une source non résolue ou non datée : elle ne va pas au brief.
  Critères détaillés : `references/source-quality.md`.

### Tier 3 — Enrichissement de l'annuaire
Un **domaine d'autorité** nouvellement confirmé au tier 2 est **proposé** pour ajout à
l'annuaire du tenant (`tenants/{tenant}/sources/authority-map.md`), validation humaine
avant intégration. C'est ce qui fait grossir le tier 1 au fil des articles. Ajouter un
domaine (où chercher), pas une URL de page (qui reste propre à un article).

## Critères de qualité d'une source

- **Primaire de préférence** : INSERM, INSEE, ministères, revues à comité de
  lecture, organismes officiels, plutôt que blogs/agrégateurs.
- **Jamais Wikipédia** : c'est un agrégateur, pas une source. Remonter à la source
  primaire qu'il cite et retenir celle-ci dans le brief.
- **Récente** quand la donnée est datée (stats, réglementations).
- **Vérifiable** : URL résolvable, auteur/organisme identifiable.
- **Pertinente** au niveau E-E-A-T du blog (voir la skill du site).

Grille détaillée par type de source (académique, institutionnel, presse, données
chiffrées) + exemples ✅/❌ : `references/source-quality.md`.

## Sortie : brief de sources

Restituer une liste structurée `sujet` / `sources[]` (`source`, `url`, `year`,
`claim`) / `lacunes[]`, chaque source reliée à la **claim** qu'elle appuie (pour que
la génération ne cite pas une source hors de son propos). **Schéma complet, exemple
rempli et flux d'injection** : `references/brief-schema.md`.

> Le brief circule **en argument** au subagent de génération (`content-generator`),
> il alimente le contenu et le champ `eeat_sources` ; il ne transite pas par
> `generation_prompt.txt`. Détail dans `references/brief-schema.md`.

## Interdits

- ❌ **Inventer une source ou un chiffre.** Une anecdote/statistique sans source
  vérifiable ne s'écrit pas (cf. Preuves d'Expérience E-E-A-T : ne pas fabriquer
  d'anecdotes chiffrées).
- ❌ **Retenir Wikipédia comme source** dans le brief — [[feedback-no-wikipedia-links]].
- ❌ **Citer/lier un domaine blacklisté** (concurrents, agrégateurs) : l'exclusion se
  joue **a priori** (étape 0 : blacklist chargée avant toute recherche, candidats
  écartés avant fetch). Le filtrage du brief final contre
  `references/blacklisted-domains.md` reste un **filet de sécurité**, pas le
  mécanisme principal ; sans alternative, abandonner la claim (→ `lacunes[]`)
  plutôt que citer un domaine interdit.
- ❌ « Consulté le [date] » dans les références restituées — [[feedback-no-consulte-le]].
- ❌ Tiret cadratin `—` — [[feedback-no-em-dash]].

## Articulation

- **Invocable seule** : « documente-moi ce sujet » → renvoie le brief de sources.
- **Appelée par l'orchestrateur** `refresh` **avant** la génération (étape
  « Recherche sources » du workflow), en amont des skills de rédaction
  ([[generate-enseigna-avis]], [[sp-ressources-gutenberg]]) qui consomment le brief.

## Dépendances à construire (backlog, ne pas bloquer dessus)

1. Étendre l'annuaire `tenants/{tenant}/sources/authority-map.md` aux autres tenants
   (existe pour `superprof-ressources`).
2. Script de constitution semi-auto (agent propose → humain valide).
3. Câblage déterministe du brief vers le générateur : aujourd'hui il circule en
   argument au subagent (voir `references/brief-schema.md`) ; un câblage à la PAA
   (`MinimalRow` → `audit_data` → section dédiée de `generation_prompt.txt`) reste à
   faire si l'on veut le rendre reproductible sans intervention.
