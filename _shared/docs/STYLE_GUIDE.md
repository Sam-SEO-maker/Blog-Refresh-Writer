# STYLE_GUIDE.md - Anti-patterns Complets

Guide détaillé des erreurs éditoriales interdites sur tous les blogs.

---

## 1. Clickbait & Survente

### ❌ Interdit

- "Révélation choc !"
- "Les experts ne veulent pas que vous sachiez ça"
- "Apprenez la guitare en 7 jours !"
- "Perdez 10 kg en 2 semaines"
- "Devenez fluent en anglais en 30 jours"
- "This one trick doctors HATE"
- "Résultats garantis ou votre argent retour"

### ✅ Correct

- Titres factuels et descriptifs
- Promesses réalistes et atteignables
- Échéances honnêtes
  - "Progressez en guitare en 3 mois avec pratique régulière"
  - "Maîtriser les accords de base en 6-8 semaines"
  - "Perte de poids progressive : 0,5-1 kg par semaine"

### Pourquoi c'est interdit

- Viole les guidelines Google sur contenu trompeur
- Détruit la confiance lecteur (promesse non tenue)
- Bounce rate élevé (lecteurs quittent déçus)
- Risque pénalité YMYL si contenu santé/finances

---

## 2. Keyword Stuffing

### ❌ Interdit

```
"Les cours de guitare, cours guitare pour apprendre guitare,
nos cours guitare professionnels guitare apprentissage guitare..."
```

```
"Avis Superprof, avis Superprof avis, test Superprof,
test avis Superprof avis test Superprof..."
```

### ✅ Correct

- Mot-clé principal 1 fois dans title
- 1-2 fois naturellement dans H2 ou introduction
- Synonymes et variantes naturels dans corps texte
- LSI keywords contextuels

**Exemple bon** :
```
Title: "Accords Guitare : Les 5 Essentiels pour Débuter"
H2: "Apprendre les cinq accords fondamentaux"
Texte: "Ces positions basiques vous permettront de jouer..."
(Au lieu de répéter "accords guitare accords guitare...")
```

### Pourquoi c'est interdit

- Pénalité algorithme Google (overdone keywords = spam)
- Lecture difficult pour humain (mauvais UX)
- Risque pénalité manuelle (spam review)

---

## 3. Formulations Vagues & Creuses

### ❌ Interdit

- "Il est crucial de..."
- "Dans le contexte actuel..."
- "Force est de constater que..."
- "Il va sans dire que..."
- "Nul besoin de rappeler..."
- "À titre informatif..."
- "Il convient de noter..."
- "D'une certaine manière..."
- "Pour dire les choses simplement..."

### ✅ Correct

- Affirmations précises et actionnables
- Voix active
- Exemples concrets
- Données chiffrées

**Transformations** :
```
❌ "Il est important d'échauffer les muscles"
✅ "L'échauffement 10 minutes réduit les blessures de 40%"

❌ "Force est de constater que le yoga aide"
✅ "Le yoga réduit l'anxiété de 35% selon une étude INSERM"

❌ "Dans un contexte actuel de..."
✅ "En 2025, 45% des Français consultent des coachs sportifs"
```

### Pourquoi c'est interdit

- Montre manque d'expertise (expert dit, pas "il faut")
- Lecture fluide détériorée
- Signal faible pour E-E-A-T (Google préfère affirmations sourcées)

---

## 4. Suppression d'Assets

### ❌ INTERDIT ABSOLU

- Réduire le nombre d'images
- Supprimer des tableaux
- Enlever des vidéos
- Retirer des liens internes

**Exemple violation** :
```
Article original : 6 images + 2 tableaux
Article révisé : 4 images + 1 tableau
❌ REJET - violation règle d'or
```

### ✅ Correct

- Conserver TOUS les assets existants
- Les mettre à jour si obsolètes (même count)
- En ajouter si pertinent (count supérieur)

**Exemple bon** :
```
Article original : 6 images, 2 tableaux
Article révisé : 6 images (mises à jour), 2 tableaux (données 2026) + 1 infographie
✅ VALIDÉ - count maintenu/augmenté
```

### Pourquoi c'est interdit

- Assets enrichissent UX ET SEO (images = durée sur page)
- Réduire assets = régression qualitative
- Peut causer baisse ranking (moins contenu riche)

---

## 5. Généralités Sans Sources (Contenu YMYL)

### ❌ Interdit

```
"Le yoga améliore la santé"
"La musculation est bonne pour vous"
"Faire du sport réduit le stress"
"Les cours particuliers aident les enfants"
```

### ✅ Correct

```
"Le yoga réduit le cortisol (hormone stress) de 35% selon une étude INSERM (2024)"
"La musculation améliore la densité osseuse de 15% en 6 mois (Journal of Sport Science, 2024)"
"L'exercice 30 min/jour réduit l'anxiété de 40% (Harvard Medical, 2025)"
"Les enfants avec soutien scolaire voient progression moyenne 20% en 3 mois (DEPP, 2024)"
```

### Pourquoi c'est interdit

- YMYL Google exige sources pour santé/finances
- Généralisations = non-crédible + risque pénalité
- Affirmation sans source = faux contenu

---

## 6. Tonalité Inadaptée

### ❌ Interdit (exemples de tonalité fausse par blog)

| Blog | Interdit | Raison |
|------|----------|--------|
| **Enseigna** | Tutoiement ("Tu dois...") | Registre : vouvoiement |
| **MyMusicTeacher** | Ton distant ou froid ("Vous devez impérativement...") | Registre : vouvoiement enthousiaste |
| **EducationetDevenir** | Ton décontracté ("C'est cool cette filière") | Registre : informatif posé |
| **Moments-Yoga** | Ton agressif ("Repousse tes limites à fond") | Registre : apaisant bienveillant |
| **CoachSportLyon** | "No pain no gain !" (toxique) | Registre : technique responsable |

### ✅ Correct

Adapter registre = "Qui suis-je ?" + "À qui je parle ?"

**Enseigna (expert journaliste)** :
```
"Nous avons testé Acadomia pendant 3 mois. Voici notre analyse détaillée."
```

**MyMusicTeacher (prof passionné)** :
```
"Bravo, vous venez de maîtriser l'accord Dm ! C'est une étape importante."
```

**EducationetDevenir (conseiller orientation)** :
```
"Cette filière offre de bons débouchés (78% insertion, ONISEP 2025).
Cependant, elle exige rigueur. Voici les réalités terrain..."
```

**Moments-Yoga (prof bienveillant)** :
```
"Écoutez votre corps. Progressez à votre rythme.
Cette posture demande de la pratique, soyez patient."
```

**CoachSportLyon (coach responsable)** :
```
"Concentrez-vous sur votre technique avant d'augmenter les charges.
L'échauffement de 10 minutes est non négociable."
```

---

## 7. Bullet Points Excessifs

### ❌ Interdit

```
Les avantages du calcul mental :
- Gain de temps
- Confiance en maths
- Utile au quotidien
- Cerveau plus rapide
- Fluidité numérique
- Independence calculatrice
- Meilleure concentration
- Compétence transférable
[continue sur 15+ points...]
```

### ✅ Correct

**Règle** : Privilégier la prose narrative. Les listes sont utiles pour les énumérations brèves, contre-indications et FAQ, mais ne doivent pas remplacer le contenu développé.

```
Transformé en paragraphe :
"Le calcul mental offre plusieurs avantages. D'abord, il libère du temps :
plus besoin de chercher une calculatrice ou poser l'opération.
Cette fluidité renforce la confiance en maths.

Ensuite, c'est une compétence transférable au quotidien.
Un élève capable d'effectuer 15 × 7 sans poser l'opération gagne
en autonomie numérique durable.

Enfin, la pratique régulière améliore la concentration et la mémoire
de travail, avec bénéfices cognitifs à long terme."
```

### Pourquoi c'est interdit

- Sections entièrement en bullet points = contenu robotique/listicle bas-de-gamme
- Prose = lecture fluide, meilleure compréhension, plus éditorial
- Les listes courtes restent utiles pour la scannabilité

---

## 8. Balises Obsolètes

### ❌ Interdit

- `<font>` (obsolète HTML5)
- `<center>` (obsolète, utiliser CSS)
- `<blink>` (jamais utiliser)
- `<u>` (souligné = confusément avec lien)
- Styles inline massifs (`<strong style="color: red; font-size: 20px;">`)

### ✅ Correct

- `<strong>` pour emphase (gras)
- `<em>` pour italique
- `<mark>` pour surbrillance
- Classes CSS pour styles
- Balises sémantiques `<h1>`, `<p>`, `<ul>`, `<table>`

---

## 9. Emojis Interdits

### ❌ Interdit DANS

- H1, H2, H3 (titre SEO)
- Meta description
- URL/slug

✅ Autorisé : Corps texte (usage modéré)

```
❌ "🎸 Apprendre la Guitare : 5 Accords 🎸"  (titre)
✅ "Voici les 5 accords 🎸 que tu dois maîtriser..."  (corps)
```

---

## 10. Empilement Rhétorique

### ❌ Interdit

```
"C'est crucial, primordial, essential et vital que vous..."
"Plusieurs, nombreux, beaucoup d'études montrent que..."
```

### ✅ Correct

- 1 seul adjectif fort par phrase
- Laisser respirer la prose
- Varier structures phrases

---

## 11. Suroptimisation Sémantique

### Principe

L'optimisation sémantique repose sur **deux axes** :
1. **Couverture** (LARGEUR) : utiliser un maximum de termes du champ sémantique du sujet. Les articles TOP 3 couvrent ~90% des termes pertinents.
2. **Modération** (PROFONDEUR) : ne pas répéter excessivement les mêmes termes. La suroptimisation rend le texte artificiel.

L'erreur la plus courante n'est PAS d'utiliser trop de termes différents — c'est de **répéter les mêmes 5-6 termes trop souvent** au lieu de varier le vocabulaire. Visez la largeur, pas la profondeur.

### Plafonds de répétition

| Élément | Limite par article (~1800 mots) |
|---------|---------------------------------|
| **Mot-clé principal** (exact match) | **3-6 occurrences** (H1 + intro + 1-2 H2 + conclusion) |
| **Top 10 termes importants** du sujet | **2-5 occurrences** chacun, distribués uniformément |
| **Autres termes du champ sémantique** | **1-3 occurrences** chacun |
| **Aucun terme** dans 3 paragraphes consécutifs | Espacer d'au moins 1 paragraphe |

### Règle de synonymie obligatoire

Tout terme apparaissant **3 fois ou plus** doit être alternativement remplacé par un synonyme ou une périphrase dans au moins 50% de ses occurrences. Exemples :
- "musculation" → "renforcement musculaire", "travail en salle", "exercices de force"
- "coach" → "entraîneur", "préparateur physique", "professionnel du sport"
- "salle de sport" → "club", "centre de fitness", "espace d'entraînement"
- "séance" → "session", "créneau", "entraînement"
- "objectifs" → "buts", "ambitions sportives", "cibles de progression"

### Cible SOSEO / DSEO (YourTextGuru)

| Métrique | Zone cible | Zone danger |
|----------|-----------|-------------|
| **SOSEO** (couverture) | **55-75%** (= zone TOP 3) | > 80% = suroptimisé |
| **DSEO** (danger) | **< 20%** (= zone TOP 3) | > 25% = keyword stuffing |

Un article à 116% SOSEO / 37% DSEO est **inexploitable**. Viser le milieu du peloton TOP 3, pas au-dessus.

### ❌ Interdit

- Empiler 3+ termes techniques dans la même phrase
- Répéter un même terme (ou proche synonyme) dans 2 paragraphes consécutifs
- Créer des phrases "catalogue" qui listent du vocabulaire spécialisé sans développer
- Forcer un terme technique là où un mot courant serait plus naturel
- Concentrer le vocabulaire spécialisé dans une seule section au lieu de le distribuer

### ✅ Correct

- Utiliser le vocabulaire spécialisé quand il apporte une précision utile au lecteur
- Préférer les périphrases et reformulations aux répétitions exactes
- Distribuer le vocabulaire technique uniformément dans l'article
- Écrire chaque phrase pour le lecteur d'abord, l'optimisation est un effet secondaire
- Laisser des paragraphes "respirer" sans terme technique (prose naturelle)

### Exemple suroptimisé vs optimal

```
❌ SUROPTIMISÉ :
"Le squat, exercice polyarticulaire d'hypertrophie, sollicite les quadriceps
lors de la flexion du genou. La charge progressive en squat avec surcharge
permet l'hypertrophie des quadriceps et fessiers. Le squat au rack favorise
la force fonctionnelle et l'endurance musculaire du bas du corps."
→ 3x "squat", 2x "hypertrophie", 2x "quadriceps" en 3 phrases

✅ OPTIMAL :
"Le squat sollicite simultanément plusieurs groupes musculaires majeurs :
quadriceps, fessiers et ischio-jambiers. C'est un mouvement fondamental
pour développer la force du bas du corps. En augmentant progressivement
la charge, vous stimulez une croissance musculaire durable."
→ 1x "squat", termes variés, lecture fluide
```

### Pourquoi c'est interdit

- Google détecte la suroptimisation sémantique (même logique que le keyword stuffing, mais distribué sur le champ sémantique)
- Lecture artificielle = signal contenu IA (bounce rate élevé)
- Un score d'optimisation sémantique optimal ≠ score maximum (la zone 60-75% surperforme le 90%+)
- Les articles TOP 3 en SERP ont un vocabulaire riche mais pas saturé

---

## Quick Checklist Anti-Patterns

Avant validation, vérifier :

- [ ] **Pas de clickbait** : Titre factuel vs promesse exagérée
- [ ] **Pas de keyword stuffing** : KW naturel, 1-2x max
- [ ] **Pas de vague creux** : Chaque affirmation concrète/sourcée
- [ ] **Assets conservés** : count_après ≥ count_avant
- [ ] **YMYL sourcé** : Sources + dates si santé/finances
- [ ] **Ton cohérent** : Registre adapté au blog
- [ ] **Pas excès bullets** : Prose narrative privilégiée
- [ ] **Balises propres** : HTML5 sémantique, pas obsolète
- [ ] **Pas emojis titre** : Emojis corps uniquement
- [ ] **Pas suroptimisé** : Aucun terme technique > 3x, pas d'empilement dans même phrase

---

*Version 2.0 - Février 2026*
