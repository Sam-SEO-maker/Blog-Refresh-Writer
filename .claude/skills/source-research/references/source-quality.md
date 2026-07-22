# Qualité d'une source — grille par type

Référence chargée à la demande depuis `recherche-sources`. Comment juger qu'une source
mérite d'entrer au brief E-E-A-T. **Principe clé** : préférer toujours la source
**primaire** (celle qui produit l'information) à un agrégateur qui la relaie.

## 1. Académique (revues, thèses, laboratoires)

Le plus haut niveau de confiance quand la source est correctement identifiée.

- ✅ Article de revue à comité de lecture, DOI résolvable, auteurs + institution
  (ex. sur hal.science, cairn.info, une revue universitaire).
- ✅ Thèse ou rapport de laboratoire signé (CNRS, INSERM, INRIA), daté.
- ❌ « Une étude a montré que… » sans nom de revue, sans auteur, sans année.
- ❌ Article prédateur / revue non indexée présentée comme « scientifique ».

Signaux de fiabilité : comité de lecture, DOI, affiliation, bibliographie vérifiable.

## 2. Institutionnel (organismes officiels, ministères)

L'ossature du E-E-A-T pour les sujets éducatifs et YMYL.

- ✅ Page d'un organisme de la whitelist (`education.gouv.fr`, `insee.fr`,
  `legifrance.gouv.fr`, `unesco.org`…) portant l'information précise.
- ✅ Rapport officiel PDF avec organisme émetteur et date en couverture.
- ❌ Reprise commerciale d'un chiffre officiel (site marchand) au lieu de l'organisme.
- ❌ Page d'accueil ou de catégorie de l'organisme, sans la donnée précise.

Whitelist de référence : `edito-refresh/references/eeat-framework.md`. Annuaire par
matière (site Ressources FR) : `sites/superprof.fr-ressources/sources/authority-map.md`.

## 3. Presse de référence

Utile pour l'actualité, le contexte, la citation d'expert. À traiter comme relais, pas
comme source primaire d'un chiffre.

- ✅ Article daté et signé d'un titre reconnu (Le Monde, Libération, Le Figaro, BBC…),
  utilisé pour un fait ou une citation attribuée.
- ✅ Servir de tremplin : remonter à l'étude/au rapport cité dans l'article et lier
  **celui-ci** pour la donnée chiffrée.
- ❌ Tribune d'opinion présentée comme un fait établi.
- ❌ Reprise de dépêche sans source primaire quand un chiffre est en jeu.

## 4. Données chiffrées (statistiques, rapports)

Une statistique n'entre au brief qu'avec **source + année**, sinon elle est réputée
obsolète par les moteurs.

- ✅ `[chiffre] + [organisme] + [année]` (ex. « Selon l'INSEE (2025), … »).
- ✅ Page de résultats/tableau de l'organisme, année de la donnée explicite.
- ❌ Chiffre sans année, ou année de publication de la page confondue avec l'année de
  la donnée.
- ❌ Chiffre « qui circule » sans producteur identifiable.

## Pièges (rejet immédiat)

- ❌ **Wikipédia comme source** : agrégateur, jamais une autorité E-E-A-T. Remonter à
  la source primaire qu'il cite et retenir celle-ci — [[feedback-no-wikipedia-links]].
- ❌ **Source non datée** quand la donnée est datable (stat, réglementation, actualité).
- ❌ **PDF/page sans auteur ni organisme** identifiable.
- ❌ **Contenu marketing déguisé** : page produit, blog d'agence, comparateur
  commercial présentés comme neutres.
- ❌ **Forums, réseaux sociaux, blogs perso non crédités** (sauf compte officiel d'une
  institution, utilisé comme tel).
- ❌ **Homepage / page de catégorie** au lieu de la page précise portant l'information
  (cf. deep-link obligatoire, `sites/superprof.fr-ressources/prompts/site.md`).

## Restitution

Ne jamais écrire « Consulté le [date] » dans les références restituées —
[[feedback-no-consulte-le]]. Chaque source retenue est reliée à la **claim** qu'elle
appuie (schéma : `brief-schema.md`).
