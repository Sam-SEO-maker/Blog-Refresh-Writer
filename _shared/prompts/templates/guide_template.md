# Template: Guide Complet

## Structure Recommandée pour Guides

### 1. Introduction (Hook + Contexte)

**Longueur** : 100-150 mots

**Éléments** :
- **Hook** : Problématique utilisateur ou statistique percutante
- **Contexte** : Pourquoi ce guide est nécessaire
- **Promesse** : Ce que l'utilisateur va apprendre
- **Teasing structure** : Annonce des grandes sections

**Exemple (MyMusicTeacher)** :
```
Vous rêvez de jouer vos morceaux préférés à la guitare, mais vous ne savez
pas par où commencer ? Vous n'êtes pas seul : 68% des adultes qui débutent
un instrument abandonnent dans les 3 premiers mois, souvent par manque de
méthode (étude Conservatoires, 2024).

Ce guide complet vous accompagne pas à pas dans votre apprentissage de la
guitare. De la sélection de votre instrument aux 5 accords essentiels,
en passant par les bonnes postures et les premiers morceaux accessibles,
découvrez une méthode progressive qui privilégie le plaisir avant la performance.
```

**Exemple (Cours-Particuliers)** :
```
Votre enfant peine en mathématiques malgré ses efforts ? Avant de penser
à un problème de niveau, examinez sa méthode de travail. Selon le DEPP
(2025), 65% des difficultés en maths au collège sont liées à des lacunes
méthodologiques, pas à un manque de capacité.

Ce guide pratique vous donne les clés pour identifier les blocages et
accompagner votre enfant efficacement. Conseils actionnables, erreurs
courantes à éviter, et ressources recommandées : tout pour l'aider à
progresser durablement.
```

---

### 2. Sections H2 Principales

Les guides doivent suivre une **progression logique** adaptée au sujet :

#### Pour Guides Pratiques (Comment Faire)

**Structure type** :

1. **Prérequis / Ce qu'il faut savoir**
   - Niveau requis (débutant, intermédiaire, confirmé)
   - Matériel nécessaire (si applicable)
   - Temps estimé (si applicable)

2. **Étapes Détaillées** (Numérotées)
   - H2 : "Étape 1 : [Action]"
   - H2 : "Étape 2 : [Action]"
   - ...
   - 3 à 7 étapes selon complexité
   - Chaque étape : 200-400 mots avec explications détaillées

3. **Conseils et Astuces**
   - Points techniques clés
   - Raccourcis ou optimisations
   - Variantes possibles

4. **Erreurs Courantes à Éviter**
   - 3-5 erreurs fréquentes
   - Pourquoi c'est une erreur
   - Comment la corriger

5. **Pour Aller Plus Loin**
   - Ressources complémentaires
   - Exercices pratiques
   - Prochaines étapes

#### Pour Guides Informatifs (Comprendre / Choisir)

**Structure type** :

1. **Définition et Contexte**
   - Qu'est-ce que [sujet] ?
   - Pourquoi c'est important
   - Données chiffrées / statistiques

2. **Critères de Choix / Points Clés**
   - 5-7 critères essentiels
   - Explication de chaque critère
   - Exemples concrets

3. **Comparaison Options** (Si Applicable)
   - Option A vs Option B vs Option C
   - Tableau comparatif
   - Avantages/Inconvénients

4. **Conseils Pratiques**
   - Recommandations actionnables
   - Cas d'usage types
   - Situations spécifiques

5. **FAQ**
   - 3-5 questions PAA
   - Réponses concises + développement

---

### 3. Éléments de Contenu

#### Listes à Puces et Numérotées

**Usage** :
- **Listes numérotées** : Étapes séquentielles, classements
- **Listes à puces** : Énumérations, critères, exemples

**Longueur** :
- Minimum 3 items, maximum 10
- Au-delà de 10 : sous-catégoriser

**Exemple** :
```markdown
### Les 5 Accords de Guitare Essentiels

1. **Do majeur (C)** : L'accord de base par excellence
   - Placement doigts : index corde 2 case 1, majeur corde 4 case 2, annulaire corde 5 case 3
   - Grattez les 5 cordes (évitez la corde 6)

2. **Ré majeur (D)** : Utilisé dans 90% des morceaux pop
   - Placement : index corde 3 case 2, majeur corde 1 case 2, annulaire corde 2 case 3
   - Grattez les 4 cordes aiguës uniquement
...
```

#### Tableaux Comparatifs

**Usage** :
- Comparaison options/produits/méthodes
- Données chiffrées structurées
- Caractéristiques techniques

**Format** : HTML `<table>` avec `<thead>` et `<tbody>`

**Exemple** :
```html
<table>
  <thead>
    <tr>
      <th>Type de Guitare</th>
      <th>Prix Débutant</th>
      <th>Meilleur Pour</th>
      <th>Difficulté</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Guitare Classique</td>
      <td>80-150€</td>
      <td>Enfants, doigts sensibles</td>
      <td>★★☆☆☆</td>
    </tr>
    <tr>
      <td>Guitare Folk</td>
      <td>100-200€</td>
      <td>Adultes, variété musicale</td>
      <td>★★★☆☆</td>
    </tr>
    <tr>
      <td>Guitare Électrique</td>
      <td>150-250€</td>
      <td>Rock, métal, blues</td>
      <td>★★★★☆</td>
    </tr>
  </tbody>
</table>
```

#### Encadrés (Tips, Warnings, Notes)

**Types** :

**💡 Astuce / Conseil** :
```html
<div class="tip">
  <h4>💡 Astuce de Pro</h4>
  <p>[Conseil pratique basé sur expérience]</p>
</div>
```

**⚠️ Attention / Avertissement** :
```html
<div class="warning">
  <h4>⚠️ Attention</h4>
  <p>[Mise en garde importante]</p>
</div>
```

**📝 Note / Information** :
```html
<div class="note">
  <h4>📝 Bon à Savoir</h4>
  <p>[Information contextuelle utile]</p>
</div>
```

#### Citations d'Experts

**Format** :
```html
<blockquote>
  <p>[Citation textuelle de l'expert]</p>
  <cite>— Prénom Nom, Titre/Fonction, Institution (Année)</cite>
</blockquote>
```

**Exemple** :
```html
<blockquote>
  <p>L'apprentissage musical développe la mémoire de travail de 15%
  et améliore les capacités cognitives à long terme, particulièrement
  chez les enfants de 6 à 12 ans.</p>
  <cite>— Dr. Sophie Martin, Neuroscientifique, INSERM (2024)</cite>
</blockquote>
```

---

### 4. FAQ (Section Obligatoire)

**Placement** : En fin de guide, avant la conclusion

**Nombre de questions** : 3 à 7 selon longueur article

**Format** :
- **H2** : "Questions Fréquentes" ou "FAQ : [Sujet]"
- **H3** : Question exacte (format PAA Google)
- **Réponse** : Paragraphe concis (50-80 mots) + développement optionnel

**Exemple** :
```markdown
## Questions Fréquentes sur l'Apprentissage de la Guitare

### Peut-on apprendre la guitare seul sans professeur ?

Oui, il est possible d'apprendre la guitare en autodidacte grâce aux
ressources en ligne (tutoriels YouTube, applications, cours en ligne).
Cependant, 70% des autodidactes développent de mauvaises postures qu'il
faut corriger plus tard (étude Conservatoires, 2024).

Un professeur, même pour quelques séances initiales, permet d'acquérir
les bonnes bases techniques dès le départ. Sur Superprof, vous trouverez
des cours adaptés à votre niveau et budget.

### Combien de temps pour jouer un morceau complet ?

Avec une pratique régulière (15-20 minutes par jour), vous pouvez jouer
votre premier morceau simple (3-4 accords) en 2 à 4 semaines. Les morceaux
plus complexes demandent 2 à 6 mois selon votre progression.

L'essentiel est la régularité : 15 minutes quotidiennes sont plus efficaces
que 2 heures le week-end.

### Le solfège est-il obligatoire pour la guitare ?

Non, le solfège n'est pas obligatoire pour jouer de la guitare. Les
tablatures permettent d'apprendre sans connaître le solfège classique.
Cependant, des notions de base (rythme, mesure, tonalité) facilitent
grandement la progression et la compréhension musicale.
```

---

### 5. Conclusion (Synthèse + Ouverture)

**Longueur** : 100-150 mots

**Éléments** :
- **Synthèse** : Rappel des points clés (3-5 bullet points)
- **Encouragement** : Motivation finale
- **CTA** (optionnel) : Prochaine étape ou ressource complémentaire
- **Ouverture** : Lien vers article complémentaire du cocon

**Exemple (MyMusicTeacher)** :
```markdown
## Conclusion : Lancez-Vous !

Apprendre la guitare est un voyage passionnant qui demande patience et
régularité. Retenez l'essentiel :

- **Choisissez une guitare adaptée** à votre morphologie et style musical
- **Maîtrisez les 5 accords de base** avant de vouloir aller trop vite
- **Pratiquez 15-20 minutes par jour** plutôt que 2 heures occasionnelles
- **Célébrez chaque progrès**, même minime

Avec ces fondations solides, vous jouerez vos premiers morceaux en
quelques semaines. Et pour aller plus loin, découvrez notre guide
<a href="/10-morceaux-faciles-guitare-debutant/">10 Morceaux Faciles
pour Débutants</a>.

Bon apprentissage ! 🎸
```

**Exemple (Cours-Particuliers)** :
```markdown
## En Résumé

Accompagner votre enfant en difficulté scolaire demande empathie et méthode.
Les points clés à retenir :

- **Identifiez la cause** : manque de méthode, lacunes, ou démotivation
- **Valorisez les efforts** plus que les résultats
- **Instaurez une routine** de travail régulière (pas de séances marathon)
- **Sollicitez de l'aide** si nécessaire (professeur particulier, orthophoniste)

Si les difficultés persistent malgré votre accompagnement, un cours
particulier peut apporter le soutien personnalisé dont votre enfant a
besoin. Trouvez un professeur adapté sur Superprof.
```

---

## Checklist Pré-Publication Guide

Avant de valider un guide, vérifier :

- [ ] Introduction avec hook + promesse claire
- [ ] Structure logique progressive (prérequis → étapes → conclusion)
- [ ] 3-7 sections H2 principales
- [ ] Assets riches (images, tableaux, listes)
- [ ] FAQ avec 3-7 PAA
- [ ] Conclusion avec synthèse + ouverture
- [ ] Sources citées si données factuelles (YMYL surtout)
- [ ] Disclaimers santé/sport si YMYL (Yoga, Sport)
- [ ] Contre-indications si postures/exercices (YMYL)
- [ ] Ton adapté au blog (tutoiement/vouvoiement, registre)
- [ ] Termes techniques expliqués
- [ ] Asset count maintenu/augmenté
- [ ] Liens internes cocons PARENT/CHILD préservés
- [ ] CTA Superprof naturel (1-2 par article, contextualisés)

---

## Optimisation GEO (Generative Engine Optimization)

Pour maximiser la visibilité dans les moteurs génératifs (ChatGPT, Gemini, Perplexity) :

1. **Réponses directes** : Répondre à la question dès les 40-60 premiers mots après H2
2. **Snippets structurés** : Listes, tableaux, encadrés facilement extractibles
3. **PAA Coverage** : Intégrer 3-5 PAA typiques Google en H2/H3
4. **Entités nommées** : Citer experts avec nom + titre + institution
5. **Données chiffrées** : Stats récentes avec sources et année
6. **Format multimodal** : Images avec alt text, tableaux, schémas

---

## Asset Preservation (Règle d'Or)

**RAPPEL CRITIQUE** : Lors du refresh d'un guide existant :

✅ **TOUJOURS** :
- Conserver toutes les images existantes
- Maintenir tous les tableaux
- Préserver tous les liens internes
- Garder les encadrés/highlights

❌ **JAMAIS** :
- Réduire le nombre d'assets
- Supprimer des images "pour alléger"
- Retirer des tableaux "pour simplifier"
- Enlever des liens internes "pas pertinents"

**Règle** : `Asset Count APRÈS ≥ Asset Count AVANT`

**Actions autorisées** :
- Mettre à jour un asset obsolète (même count)
- Ajouter de nouveaux assets (count supérieur) ✅ ENCOURAGÉ
