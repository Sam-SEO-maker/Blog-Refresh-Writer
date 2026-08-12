---
name: qc-sp-ressources
description: >-
  Checklist QC post-génération pour les articles Superprof Ressources (format
  Gutenberg maison). Vérifie les défauts récurrents avant push WP : count-up
  numérique, H3 non isolé, "?" sur les questions, emoji en tête de FAQ, timeline
  pour les chronologies, CSV pour les tableaux, ton "tu", pas de tiret cadratin.
  Lecture seule (relecture d'un .gutenberg.html), aucun effet de bord.
disable-model-invocation: false
---

# QC Superprof Ressources — checklist post-génération

Relecture éditoriale d'un article **Superprof Ressources** au format Gutenberg
maison, **avant intégration WordPress**. Cette skill reproduit la relecture
manuelle que l'utilisateur faisait un article à la fois (défauts consolidés sur
le lot 2026-06-15). Elle est **déterministe** : chaque point a un test regex
applicable sur le fichier `{slug}_refreshed.gutenberg.html`.

> **Périmètre.** Ceci est le QC **éditorial / format**. Il ne remplace PAS le QC
> **sémantique** `cw ytg qc` (SOSEO/DSEO vs guide YTG, verdicts
> OPTIMAL/NEEDS_FIX/BLOCKED). Les deux sont complémentaires : lancer le QC
> sémantique pour la couverture de mots-clés, cette checklist pour la conformité
> de forme.

## Cible

- Fichier : `sites/superprof.fr-ressources/outputs/html/{batch}/{slug}_refreshed.gutenberg.html`
  (le `.gutenberg.html`, pas le HTML nu de debug qui est supprimé après génération).
- Blog : `superprof.fr-ressources` uniquement.

## Checklist (6 défauts récurrents + rappels transverses)

### 1. Count-up = un VRAI nombre
`countUpNumber` (attribut JSON du bloc `wp:advgb/count-up`) et le
`<span class="advgb-counter-number">` doivent **commencer par un chiffre** : le
compteur anime un nombre. Bannir le texte (« la Terminale », « cycle 4 »,
« la 2de ») et les formules (« ∇·B = 0 »). Mettre une statistique chiffrée
pertinente (ex. « 4 » formes indéterminées).

- **Test** : extraire `"countUpNumber":"…"` et vérifier que la valeur (après
  strip) commence par `[0-9]`. Idem pour le contenu de `advgb-counter-number`.
- Réf. format : [[feedback-advgb-block-format]].

### 2. Pas de H3 isolé dans un H2
Une section `<h2>` ne doit **jamais** contenir un seul `<h3>` (red flag SEO) :
soit **≥ 2 H3**, soit **aucun**.

- **Fix** : démoter le H3 isolé en `<p><strong>…</strong></p>`.
- **Test** : segmenter par H2, compter les H3 de chaque segment, signaler tout
  segment à exactement 1 H3.

### 3. Questions → point d'interrogation
Tout titre/label interrogatif (Comment, Pourquoi, Qu'est-ce que, Qui, Quel,
Combien, Où, Quand…) finit par « ?» (convention FR : **espace insécable + ?**).
Le `?` se place **avant** l'emoji final s'il y en a un (« … vieux continent ? 📜 »).

- **Test** : pour chaque `<h2>`/`<h3>` commençant par un mot interrogatif,
  vérifier la présence d'un `?` (avant tout emoji de fin).

### 4. Emoji en tête de chaque question de FAQ
Dans la section FAQ / « Questions fréquentes », **chaque question (H3) commence
par un emoji de tête**, comme les autres H2/H3 du corps.

- **Palette rotative** (varier d'une question à l'autre) : 🤔 💡 🔍 📌 🧐 📖 ❓ 💬.
- **Test** : dans le bloc FAQ, vérifier que chaque `<h3>` débute par un emoji.
- Réf. : [[feedback-faq-question-emoji]].

### 5. Chronologies → bloc Timeline
Quand un contenu est une suite de dates/événements (« dates clés », « grandes
étapes »), coder un `wp:superprof/timeline-block` — **pas** une infobox, une
liste ou un tableau.

- **Format canonique** : `sites/superprof.fr-ressources/prompts/site.md`
  (bloc `wp:superprof/timeline-block`, ~l. 298).
- **Règle des infobox** : si un timeline **remplace** une infobox, conserver
  **1 infobox bleue + 1 jaune** (ajouter une infobox de remplacement ou recolorer
  une existante).
- **Test** : détecter les listes/tableaux de dates dans le corps → doivent être
  des timeline ; vérifier qu'il reste ≥ 1 infobox bleue et ≥ 1 jaune.

### 6. Au moins un tableau, et un CSV par tableau
**Zéro tableau = À CORRIGER, toujours.** Un article sans `<table>` est
incomplet, même si le sujet ne paraît pas tabulaire et même si l'original
n'en avait aucun : il y a toujours une comparaison, une série de critères,
un jeu de cas ou un récapitulatif de formules à mettre en grille. Cible 1 à 3,
**3 maximum** (exception lexique/grammaire). Chaque `<table>` a son **CSV**
associé (`{slug}_tableau_{descriptif}.csv`), généré par l'extracteur du
pipeline et jamais à la main.

- **Test 1** : `grep -c '<!-- wp:table' f` → si `0`, **À CORRIGER** (proposer
  le tableau manquant : colonnes + section H2 d'accueil).
- **Test 2** : compter les `<table>` et vérifier la présence d'un CSV par tableau.
- **Test 3 (format)** : `grep -c 'figure class="wp-block-table"' f` → doit valoir
  `0`. Un `<table>` doit être l'enfant **direct** du bloc `<!-- wp:table -->`, et
  `class="has-fixed-layout"` n'est admis qu'avec `{"hasFixedLayout":true}` dans
  les attributs du bloc — sinon l'éditeur affiche « block seems broken ».
- **Test 4 (hors bloc)** : tout `<table>` sans `<!-- wp:table -->` juste avant est
  invisible pour l'extracteur CSV **et** bascule en `core/freeform` dans WP.
- Réf. : [[feedback-csv-naming-tablepress]].

## Rappels transverses (déjà connus, à re-vérifier)

- **Accents corrects partout**, y compris dans le JSON des blocs (jamais
  « ameliorer » / « systeme »).
- **Jamais de tiret cadratin `—`** dans le contenu — [[feedback-no-em-dash]].
- **Ton « tu » + emojis** dans les H2/H3 — [[feedback-sp-ressources-gutenberg-house-format]].
- **Blocs AdvGB au format exact** (commentaires `<!-- wp:advgb/* -->`, HTML sur
  une seule ligne, `{uuid}` cohérent JSON↔classe CSS) — [[feedback-advgb-block-format]] ;
  référence canonique `sites/superprof.fr-ressources/.claude/skills/sp-ressources-gutenberg/references/reference-gutenberg.md`.
- **6 blocs obligatoires** : 2 infobox (1 bleue + 1 jaune), 1 count-up, 1 citation,
  **≥ 1 tableau**, 1 bloc sources — [[feedback-sp-ressources-gutenberg-house-format]],
  [[feedback-sp-sources-block-format]].
- **`countUpNumber` commence par un chiffre** et reste parseable comme nombre :
  `"1,25"`, `"10³⁶"`, `"40 ans"`, `"0,62 à 0,78"` cassent le compteur. Mettre le
  nombre nu dans `countUpNumber`, l'unité et les nuances dans `descText`.
- **Formulations positives** (jamais « pas de panique », « dans ce cours ») —
  [[feedback-language-tone-sp-ressources]].
- **Pas de blocs Gutenberg identiques adjacents** (un par section H2 max, cf.
  règle Séraphine transposable).

## Sortie attendue

Un rapport par article listant, pour chaque point : **OK** / **À CORRIGER** avec
l'extrait fautif et le fix suggéré. Ne modifie rien : c'est une relecture. Pour
appliquer les corrections, déléguer à la génération/correction (subagent), pas à
cette skill.

## Sources de vérité

- Mémoire pivot : [[feedback-sp-ressources-qc-checklist]] (lot 2026-06-15).
- Format maison : [[feedback-sp-ressources-gutenberg-house-format]].
- Blocs AdvGB : [[feedback-advgb-block-format]].
- FAQ emoji : [[feedback-faq-question-emoji]].
- Prompt principal : `sites/superprof.fr-ressources/prompts/site.md`.
- Référence HTML canonique :
  `sites/superprof.fr-ressources/.claude/skills/sp-ressources-gutenberg/references/reference-gutenberg.md`.
