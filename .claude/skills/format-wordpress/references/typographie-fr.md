# Typographie & mécanique du français

Mécanique **de langue** pour tout contenu français (tous tenants FR) : espaces
insécables, guillemets, apostrophe, nombres, casse, connecteurs IA à bannir,
anglicismes. Importée du paquet `blog-refresh.skill` (juillet 2026) et adaptée aux
règles du repo. Complète le `SKILL.md` de `format-wordpress` (invariants HTML/WP) ;
la connaissance pays (système scolaire, vocabulaire métier) vit côté tenant
(ex. `connaissance-fr.md` de [[sp-ressources-gutenberg]]).

## 1. Espaces insécables (NBSP)

Le français exige une **espace insécable avant** ces signes (contrairement à
l'anglais) :

| Signe | Forme | Exemple |
|---|---|---|
| `:` `;` `?` `!` | `texte⎵:` | `Le résultat⎵: 15/20` |
| `%` | `nombre⎵%` | `15⎵%` |
| `€` | `nombre⎵€` | `30⎵€` |
| `«` `»` | `«⎵texte⎵»` | NBSP à l'intérieur des guillemets |

Où `⎵` = espace insécable (U+00A0). Dans le HTML de sortie, utiliser le caractère
U+00A0 littéral ou `&nbsp;` — ne pas compter sur l'auto-correction de WordPress au
collage. Les vieux articles ont souvent des NBSP manquantes : détecter et corriger
au refresh.

## 2. Guillemets

- **« … » (guillemets français)** pour les citations directes et titres d'œuvres
  dans le corps, avec NBSP intérieures.
- **" … " (guillemets anglais)** : à éviter dans du texte français — signe de
  texte traduit ou généré.
- **' … '** : uniquement à l'intérieur d'une citation anglaise imbriquée.

## 3. Apostrophe

Apostrophe **typographique** `'` (U+2019), jamais droite `'` (U+0027) :
`aujourd'hui`, `l'oral`.

## 4. Tirets

- **Tiret cadratin `—` : interdit partout** (tous tenants, corps et JSON) —
  [[feedback-no-em-dash]]. Pour les incises : virgules, parenthèses, ou tiret
  demi-cadratin `–` si un séparateur visuel est indispensable.
- **Tiret demi-cadratin `–`** : plages de nombres (`pages 12–15`, `2010–2024`),
  jamais comme béquille de rythme dans la prose.

## 5. Écriture inclusive — point médian

Le **point médian** est autorisé quand il reste naturel : `un·e prof·e
expérimenté·e`, `chaque étudiant·e`, `devenir fort·e en espagnol`.

- **Préférer d'abord la reformulation** qui évite le genre (mot épicène, tournure
  neutre) ; le point médian sert quand la reformulation alourdit plus qu'elle n'aide.
- Éviter l'enchaînement de plusieurs formes à point médian dans une même phrase
  (illisible), et dans les **headings** (nuit à la scannabilité).
- Caractère : **point médian typographique** `·` (U+00B7), pas un point.
- Cohérence par article : si l'article d'origine en use, poursuivre ; sinon,
  décision par article selon l'audience.

## 6. Nombres

| Format | Règle | Exemple |
|---|---|---|
| Milliers | espace insécable | `1⎵234⎵567` |
| Décimale | virgule | `12,5` |
| Monnaie | `30⎵€`, jamais `€30` | |
| Pourcentage | `15⎵%` | |
| Téléphone | espaces par paires | `01 23 45 67 89` |

- **Zéro à neuf** : en lettres (`trois élèves`) ; **10 et plus** : en chiffres.
- Statistiques, prix, pourcentages, dates : toujours en chiffres.
- Dates : `le 15 mars 2026` (corps de texte) ou `15/03/2026` ; jamais ISO
  `2026-03-15` ni format US dans la prose.

## 7. Italiques

Uniquement pour : mots étrangers insérés dans une phrase française (`un effet
*flow*`, `*et al.*`) et titres d'œuvres (`*Les Misérables*`). **Jamais pour
l'emphase** — gras avec parcimonie à la place.

## 8. Casse

- **Minuscule** : langues (`l'espagnol`), matières (`les mathématiques`), niveaux
  (`la terminale`), jours et mois (`lundi 15 mars`, `en septembre`).
- **Majuscule** : noms d'examens (`le Baccalauréat`, `le Brevet`, `le Bac`),
  institutions (`l'Éducation nationale`).
- **Titres et headings : sentence case**, jamais Title Case.
  - ✅ `Oral d'espagnol au bac : exemples de thèmes et conseils`
  - 🚫 `Oral d'Espagnol au Bac : Exemples de Thèmes et Conseils`

## 9. Connecteurs IA à bannir (FR)

Tics de texte généré — détecter et remplacer par du natif :

| Tic IA | Alternative |
|---|---|
| Il est important de noter que | (supprimer) / À noter |
| En outre | Et / D'ailleurs |
| Par ailleurs | D'ailleurs / Or |
| De plus | Et / En plus |
| Il convient de mentionner | (supprimer) / On peut citer |
| Dans le cadre de | Pour / Lors de |
| Au niveau de | Sur / Pour |
| Force est de constater | (supprimer) / Manifestement |
| Plonger dans (l'univers de) | Découvrir / Explorer |
| Tisser des liens | Créer des liens |
| Naviguer (les complexités) | Avancer dans / Traverser |
| Embrasser (le défi) | Relever / S'attaquer à |
| En effet | (souvent supprimable) / De fait |
| C'est-à-dire que | Autrement dit |
| Dans un monde où… | (cliché d'ouverture — attaquer le sujet directement) |

**Connecteurs qui sonnent natif** : D'ailleurs · Or · En revanche · Cela dit ·
Reste que · À vrai dire · Quand même · Bref · Au fond. (`Du coup` : familier,
avec parcimonie.)

**Remplissage à couper** : `tout simplement`, `très très`, `assez` / `un peu` /
`vraiment` / `bien` quand ils n'apportent rien.

## 10. Fautes courantes à détecter au refresh

| Anti-pattern | Correction |
|---|---|
| tu/vous mélangés dans un article | choisir selon l'audience (et la skill du tenant), uniformiser |
| `Lundi`, `Septembre` en cours de phrase | minuscule |
| `L'Espagnol` (la langue) | `l'espagnol` |
| `15%`, `30€` | NBSP : `15⎵%`, `30⎵€` |
| `« texte »` avec espaces normales | NBSP intérieures |
| `"texte"` anglais dans du français | `«⎵texte⎵»` |
| Apostrophe droite `'` | typographique `'` |
| Tout `—` | interdit — virgules, parenthèses ou `–` ([[feedback-no-em-dash]]) |
| « challenger » (verbe) | défier, remettre en question |
| « checker » | vérifier |
| « supporter » (soutenir) | soutenir, appuyer |
| « performer » (verbe) | réussir, donner le meilleur |

## 11. Anglicismes tolérés

Entrés dans l'usage, moins disruptifs que leur traduction : le coach / coacher
(« entraîneur » préféré pour le sport) · le brief · le marketing · le management ·
le test · le job (familier — préférer « travail »/« poste » en registre soutenu).
Les emprunts non naturalisés s'écrivent en italique : `un *workflow* fluide`,
`le *small talk*`.
