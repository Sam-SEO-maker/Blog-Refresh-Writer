---
name: generate-enseigna-avis
description: >-
  Rédige/refreshe un article d'avis Enseigna (review d'un service de soutien
  scolaire). Impose la structure canonique (intro → H2 d'analyse → pros/cons →
  note → verdict rapide en fin → FAQ), l'export des données structurées en ACF
  JSON, les tableaux en CSV, et les interdits Enseigna. Transformation lourde,
  déléguée au subagent de génération. Invoquer via /generate-enseigna-avis.
disable-model-invocation: true
---

# Génération article avis — Enseigna

Produit un article **avis/review** pour `enseigna.fr` (soutien scolaire). Ton :
testeur à la **première personne du singulier** (« j'ai testé », « j'ai relevé »,
« je préfère »), **vouvoiement du lecteur**. Le testeur est **une personne
avec une situation concrète** (apprenant, parent) qui raconte son parcours sur
le service à d'autres élèves : vécu, attentes, impressions et préférences sont
libres ; **tout fait vérifiable** (tarif, effectifs, conditions, chiffre,
citation) vient d'une source réelle de `sources_brief.md`. L'intro part d'une
situation humaine, jamais d'une institution ni d'un chiffre, et n'annonce pas
le plan. Modèle de ton : https://enseigna.fr/avis-superprof-soutien-scolaire/.
Détail de la règle, tics interdits et exemples ❌/✅ : sections « Persona »,
« Personne et voix » et « Mots interdits » de `site.md`.
YMYL medium. Cette skill porte la **structure et les interdits** ; le fond
(stats, experts, vocabulaire) vient du prompt site.

> **Source de vérité (à référencer, pas dupliquer)** :
> `sites/enseigna.fr/prompts/site.md` (prompt principal),
> `sites/enseigna.fr/prompts/blocks/acf-fields-template.md` (template ACF),
> `sites/enseigna.fr/prompts/blocks/*.html` (blocs de référence : pros-cons,
> references, blockquote…). Articles de référence publiés :
> `sites/enseigna.fr/outputs/html/avis/` (GoStudent, Complétude).

## Deux types d'article (deux sous-dossiers de sortie)

Le site enseigna produit **deux types** d'articles, chacun avec son prompt et son
sous-dossier de sortie HTML :

| Type | Prompt principal | Sortie HTML |
|---|---|---|
| **Avis** (review d'une plateforme) | `sites/enseigna.fr/prompts/site.md` | `sites/enseigna.fr/outputs/html/avis/` |
| **Versus** (comparatif A vs B) | `sites/enseigna.fr/prompts/vs_concurrent.md` | `sites/enseigna.fr/outputs/html/versus/` |

Cette skill couvre le type **avis**. Un article **versus** suit `vs_concurrent.md`
et écrit dans `html/versus/`. Les dossiers **`acf/`, `csv/`, `metadata/` restent
communs** aux deux types (clés par slug).

## Livrables (3 fichiers par article — type *avis*)

1. `sites/enseigna.fr/outputs/html/avis/{YYYY-MM-DD}/{slug}_refreshed.gutenberg.html`
   (sous-dossier de batch daté ymd, ex. `2026-07-08`) — **corps**,
   liste plate de blocs Gutenberg. **PAS de `<h1>` dans le corps** (le H1 est un
   champ ACF sur Enseigna) : le corps commence par le paragraphe d'introduction.
   Pas de fiche technique dans le corps.
2. `sites/enseigna.fr/outputs/acf/{slug}_acf.json` — **données structurées** ACF
   (voir template). Champs clés : `h1` (style « Avis {Site} : mon test des cours
   de … sur {Site} »), `nom_du_site`, `note_globale_5` (= verdict /10 ÷ 2 ;
   **concurrent plafonné à 4/5**), `note_service_client`, `annee_creation`,
   `prix_mensuel_moyen`, avis positif/neutre/négatif (date + texte), etc.
   `note_globale_5` **doit** correspondre au verdict /10 du corps (cohérence rich
   snippet).
   **Clés = strictement celles du template**, jamais de clé inventée
   (`statuts_enseignants`, `politique_annulation`, `commentaire_avis`… sont
   des champs qui n'existent pas dans WordPress et sont perdus). **Valeurs =
   valeurs de fiche technique, pas des phrases** : un prix est un nombre entier
   arrondi (« 14 € », moyenne de la fourchette si le tarif varie, fourchette
   reportée dans `asterisque_prix` en une ligne), un nombre de cours est un
   nombre, un téléphone absent est « Non communiqué », les dates d'avis au
   format `JJ/MM/AAAA`, les verbatims d'avis en une phrase + attribution.
3. `sites/enseigna.fr/outputs/csv/{slug-à-tirets}_tableau_{colonnes}.csv` — `{colonnes}`
   = les en-têtes du tableau en minuscules sans accents, reliés par `_`
   (ex. `_tableau_critere_note_commentaire.csv`), pour retrouver le bon
   fichier dans le Finder ; jamais un nom « descriptif » inventé. Chaque
   `<table>` du corps exporté en CSV (dossier **`csv/`**, jamais `tables/`), **max
   3/article**. Aucun shortcode `[table id=X /]` dans le HTML : les rédacteurs
   importent le CSV dans TablePress puis insèrent en mode code. Réf.
   [[feedback-csv-naming-tablepress]].

> `push_to_wp.py` lit encore `metadata/{slug}_metadata.json` pour les meta
> SEOPress (title/desc) — le conserver tant que le push REST l'utilise, même si
> la fiche technique Gutenberg, elle, est supprimée. Réf.
> [[feedback-fiche-technique-separation]].

## Structure de l'article (ordre canonique)

Suivre les **articles de référence publiés**, PAS `review_template.md` :

1. **Intro** : 2-3 `<!-- wp:paragraph --><p>…</p>` sans classe.
2. **Premier H2 structurant** (« Ce que j'ai évalué » / « Ce que disent les
   avis »), puis les H2 d'analyse.
3. **Fin d'article** : pros/cons (`wp:columns`) → note finale → **verdict rapide**
   (`<!-- wp:html --><div class="verdict-rapide">…</div>`) → **FAQ**.
   Le verdict rapide va à la **FIN, avant la FAQ** — jamais au début. Réf.
   [[feedback-enseigna-verdict-rapide-position]].

**Convention pros/cons.** À la **génération**, écrire le `div` brut :
`<div class="pros-cons"><div class="cons"><h3>Les -</h3>…</div><div class="pros"><h3>Les +</h3>…</div></div>`.
`cw finalize` le convertit ensuite en blocs `wp:columns` — c'est cette forme
convertie, et elle seule, qui part en production :

```
<!-- wp:columns {"className":"pros-cons-wrapper"} -->
<div class="wp-block-columns pros-cons-wrapper">
<!-- wp:column {"className":"cons-block"} -->…<!-- /wp:column -->
<!-- wp:column {"className":"pros-block"} -->…<!-- /wp:column -->
</div>
<!-- /wp:columns -->
```

> ⚠️ **Un `.gutenberg.html` qui contient encore `<div class="pros-cons">` n'est
> pas publiable** : WordPress le rangerait en bloc « HTML classique », non
> éditable en colonnes. Le cas se produit quand le fichier est édité à la main
> **après** le dernier passage de `finalize`. Contrôle avant publication :
> `grep -c 'pros-cons-wrapper'` doit renvoyer 2, et `grep -c 'class="pros-cons"'`
> doit renvoyer 0. Même logique pour `div.verdict-rapide`, qui reste lui
> volontairement dans un bloc `wp:html`.

**Liste de matières/activités avec émojis** : quand la plateforme testée couvre
plusieurs matières ou disciplines (langues, soutien scolaire, loisirs…), en
lister quelques-unes avec un émoji devant chaque nom, pour illustrer
concrètement la diversité de l'offre — format `emoji Nom`, une ligne par
item, sans description ajoutée. Référence publiée : `/avis-superprof-loisirs/`
(section sur l'abonnement Pass Élève) :
```
🎹 Piano
🎸 Guitare
🕺 Danse
🏊‍♀️ Natation
🔮 Tarot
🧵 Macramé
🎻 Viole de gambe
🧗‍♀️ Escalade
🛼 Roller
```
Choisir des émojis pertinents pour les matières réellement citées dans la
source vérifiée (ne pas inventer de matières hors brief), viser 6-10 items
pour donner une impression de diversité sans noyer l'article.

## Interdits Enseigna (ne jamais produire)

- ❌ **Déclaration d'indépendance éditoriale** (`div.independence-statement`) —
  ignorer la section 8 de `review_template.md`. Réf.
  [[feedback-no-independence-declaration]].
- ❌ **Callouts / CTA colorés** (`wp:html` avec `#4caf50` / `#fff9e6` / `#e8f4f8`)
  — ancien système. Réf. [[feedback-no-callouts-cta]].
- ❌ **H1 dans le corps** (H1 = champ ACF).
- ❌ Note concurrent > 8/10 (→ > 4/5 en ACF).

## Règles transverses

- **Refresh = jamais supprimer d'asset ni de lien** (Règle d'Or), y compris les
  liens vers concurrents (superprof.fr) — [[feedback-refresh-no-link-removal]].
- **H2 optimisés**, pas recopiés de l'article source (sauf H2 = H1 d'un enfant de
  cocon) — [[feedback-h2-optimization]].
- **Accents corrects** partout (HTML et JSON ACF).
- **Pas de tiret cadratin `—`** — [[feedback-no-em-dash]].
- **Pas de « Consulté le [date] »** dans les sources — [[feedback-no-consulte-le]].
- **Pas de `<strong>` dans les ancres de liens**, pas de lien dans les H2/H3.
- **Listes à puces** : chaque `<li>` finit par une virgule, le dernier par un point.

## Exécution

Générer via **subagent Claude Code** (abonnement Max), jamais l'API payante.
Le subagent lit ce SKILL.md + `site.md` + le HTML source + les données GSC,
écrit directement les 3 fichiers, et ne renvoie pas de HTML dans le chat.

## Sources de vérité

- Structure/interdits : mémoires liées ci-dessus.
- Prompt & ACF : `sites/enseigna.fr/prompts/site.md`,
  `sites/enseigna.fr/prompts/blocks/acf-fields-template.md`.
- Référence visuelle : `sites/enseigna.fr/outputs/html/avis/`.
