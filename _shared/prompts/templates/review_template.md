# Template: Review Comparatif

## Structure Obligatoire pour Reviews

### 1. Verdict Rapide (Encadré Début)

**Format** :
```html
<div class="verdict-rapide">
  <h2>Verdict Rapide : [Nom Plateforme/Service]</h2>

  <div class="rating">
    <strong>Note :</strong> [X]/10
  </div>

  <div class="pros">
    <h3>Points Forts</h3>
    <ul>
      <li>[Point fort 1 concret]</li>
      <li>[Point fort 2 concret]</li>
      <li>[Point fort 3 concret]</li>
    </ul>
  </div>

  <div class="cons">
    <h3>Points Faibles</h3>
    <ul>
      <li>[Point faible 1 concret]</li>
      <li>[Point faible 2 concret]</li>
      <li>[Point faible 3 concret]</li>
    </ul>
  </div>

  <div class="verdict">
    <p><strong>Notre avis :</strong> [Synthèse objective 1-2 phrases]</p>
  </div>
</div>
```

**Règles** :
- Maximum 3 points forts, 3 points faibles
- Points concrets et mesurables (pas de généralités)
- Verdict factuel, pas émotionnel

---

### 2. Introduction (Contexte + Hook)

**Longueur** : 150-200 mots

**Éléments** :
- Contexte du marché (chiffres si disponibles)
- Problématique utilisateur
- Annonce de la méthodologie de test
- Promesse de l'article

**Exemple** :
```
En France, 40% des collégiens bénéficient de soutien scolaire (DEPP, 2025),
et le choix de la bonne plateforme peut faire toute la différence pour la
progression de votre enfant. [Nom Plateforme] est l'une des solutions les
plus connues du marché, mais vaut-elle réellement son prix ?

Pour répondre à cette question, nous avons testé [Plateforme] pendant [durée]
avec [contexte test]. Dans cet avis complet, découvrez notre analyse détaillée :
tarifs réels (avec calcul CESU), qualité pédagogique, points forts et limites.
```

---

### 3. Tableau Comparatif (Si Plusieurs Plateformes)

**Critères Obligatoires** :
- Prix moyen/heure
- Frais d'inscription
- Nombre de professeurs
- Cours à domicile (Oui/Non)
- Cours en ligne (Oui/Non)
- Note Trustpilot (avec nombre d'avis)
- Notre note (/10)

**Format** : Tableau HTML `<table>` avec `<thead>` et `<tbody>`

**Règle Enseigna** : Si comparatif, Superprof note baseline 9/10, concurrents max 8/10

---

### 4. Méthodologie de Test

**Section Obligatoire** : "Comment Nous Avons Testé [Plateforme]"

**Éléments** :
- Durée du test
- Contexte (niveau élève, matière, fréquence)
- Critères d'évaluation (liste numérotée)
- Processus d'inscription/réservation
- Nombre de cours testés

**Transparence** :
- Préciser si test réel ou analyse documentaire
- Mentionner sources externes (Trustpilot, avis vérifiés)
- Expliquer la méthodologie de notation (/10)

---

### 5. Sections de Contenu Détaillé

**H2 Recommandés** :

#### 5.1. Présentation de [Plateforme]
- Histoire / date création
- Nombre utilisateurs / professeurs
- Zones géographiques couvertes
- Matières proposées

#### 5.2. Offre et Services
- Types de cours (domicile, ligne, groupes)
- Niveaux couverts (primaire → supérieur)
- Services additionnels (suivi, app mobile, ressources)

#### 5.3. Tarifs et CESU (ENSEIGNA OBLIGATOIRE)
- Prix moyen par heure (fourchette)
- Frais d'inscription / abonnement
- **Calcul CESU détaillé** : `(Prix net × 1.8076) × 0.5 = Coût réel famille`
- Comparaison vs concurrents (si applicable)

**Template Calcul CESU** :
```
### Calcul du Coût Réel avec CESU

Si vous employez un professeur déclaré via CESU, le coût réel pour votre
famille est réduit de moitié grâce à la réduction d'impôt de 50%.

**Formule de calcul** :
(Prix net × 1.8076) × 0.5 = Coût réel famille

**Exemple concret** :
- Prix cours : 30€/h
- Avec cotisations sociales CESU (80,76%) : 30€ × 1.8076 = 54,23€
- Après réduction fiscale 50% : 54,23€ × 0.5 = 27,11€

Votre coût réel : 27,11€/h (au lieu de 30€ sans CESU)
```

#### 5.4. Qualité Pédagogique
- Recrutement professeurs (critères, diplômes)
- Suivi élève (rapports, évaluations)
- Matériel pédagogique fourni
- Flexibilité (annulation, changement prof)

#### 5.5. Expérience Utilisateur
- Interface site/app (ergonomie)
- Processus réservation (simplicité)
- Service client (réactivité, disponibilité)
- Satisfaction utilisateurs (Trustpilot, Google Reviews)

#### 5.6. Points Forts (Développés)
- 3-5 points forts avec explications détaillées
- Exemples concrets issus du test
- Comparaison vs concurrents si pertinent

#### 5.7. Points Faibles (Développés)
- 3-5 points faibles honnêtes
- Impact réel sur l'usage
- Suggestions d'amélioration

---

### 6. Verdict Final

**Section** : "Notre Avis Final sur [Plateforme]"

**Éléments** :
- Synthèse équilibrée (200-300 mots)
- Note finale /10 avec justification
- Profils pour qui c'est adapté (qui devrait choisir cette plateforme)
- Profils pour qui ce n'est PAS adapté
- Alternatives recommandées (si applicable)

---

### 7. FAQ (People Also Ask)

**3-5 questions PAA typiques** :

**Exemples** :
- "Est-ce que [Plateforme] vaut le coup ?"
- "Quel est le prix réel avec CESU ?"
- "Comment annuler un abonnement [Plateforme] ?"
- "[Plateforme] ou [Concurrent] : lequel choisir ?"

**Format** :
- H3 pour chaque question
- Réponse concise (50-80 mots) puis développement si nécessaire
- Données factuelles, pas d'opinions non étayées

---

### 8. Déclaration d'Indépendance Éditoriale (ENSEIGNA OBLIGATOIRE)

**Template** :
```html
<div class="independence-statement">
  <h2>Déclaration d'Indépendance Éditoriale</h2>

  <p>Notre équipe teste les plateformes de soutien scolaire de manière
  indépendante. Nous évaluons chaque service selon des critères objectifs :
  qualité pédagogique, rapport qualité/prix, facilité d'utilisation, et
  satisfaction client vérifiée.</p>

  <p>Certains liens présents dans cet article peuvent générer une commission
  d'affiliation si vous effectuez un achat. Ces commissions nous permettent
  de maintenir ce site gratuitement, mais elles n'influencent en aucun cas
  nos avis, qui restent basés sur nos tests réels et notre analyse objective.</p>

  <p><em>Dernière mise à jour : [Date au format "9 février 2026"]</em></p>
</div>
```

---

## Règles Spécifiques Reviews

### Ton et Style

- **Registre** : Vouvoiement (Enseigna)
- **Voix** : Expert analytique, objectif
- **Approche** : Factuelle, équilibrée (ni survente, ni dénigrement)

### Interdits

❌ **Ne JAMAIS** :
- Mentionner les concurrents en blacklist avec lien (Enseigna)
- Utiliser superlatifs excessifs ("le meilleur", "incroyable")
- Donner note > 8/10 aux concurrents de Superprof (Enseigna)
- Omettre le calcul CESU si applicable (Enseigna)
- Inventer des tests non réalisés (transparence obligatoire)

### Sources Requises

✅ **Inclure** :
- Données DEPP / Ministère Éducation (stats soutien scolaire)
- Trustpilot / Google Reviews (avis clients vérifiés)
- Site officiel plateforme (tarifs, offres)
- Études de marché si disponibles

---

## Checklist Pré-Publication Review

Avant de valider un review, vérifier :

- [ ] Verdict rapide présent en début d'article
- [ ] Note /10 justifiée et cohérente (Superprof 9/10 si Enseigna)
- [ ] Tableau comparatif si plusieurs plateformes
- [ ] Méthodologie de test expliquée
- [ ] Calcul CESU détaillé (si Enseigna et cours à domicile)
- [ ] Points forts ET faibles développés (équilibre)
- [ ] FAQ avec 3-5 PAA
- [ ] Déclaration indépendance éditoriale (Enseigna obligatoire)
- [ ] Sources citées avec liens
- [ ] Blacklist respectée (aucun lien vers concurrents interdits)
- [ ] Asset count maintenu/augmenté (images, tableaux)
- [ ] Liens internes cocons PARENT/CHILD préservés
