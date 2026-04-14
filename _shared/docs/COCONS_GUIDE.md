# COCONS_GUIDE.md - Maillage Sémantique Détaillé

Guide complet des cocons sémantiques PARENT/CHILD avec exemples et structures.

---

## Principe PARENT/CHILD

Un **cocon sémantique** = structure maillage interne thématique où :
- **1 article PARENT** (pilier, général) pointe vers
- **N articles CHILD** (détaillés, spécifiques)

**Règle d'or** : **H2 du PARENT = H1 du CHILD** (colonne vertébrale)

---

## Exemple Complet : Cocon Guitare (MyMusicTeacher)

### Structure Arbre

```
PARENT: "Apprendre la Guitare : Guide Complet Débutant" (H1)
├─ H2: "Choisir sa première guitare"
│    └─→ CHILD: "Quelle Guitare pour Débuter ?" (H1)
│
├─ H2: "Les 5 accords de base"
│    └─→ CHILD: "Les 5 Accords de Guitare Essentiels" (H1)
│
├─ H2: "Apprendre le solfège"
│    └─→ CHILD: "Solfège Guitare : Est-Ce Obligatoire ?" (H1)
│
├─ H2: "Premiers morceaux faciles"
│    └─→ CHILD: "10 Morceaux Guitare Débutant" (H1)
│
└─ H2: "Progresser rapidement"
     └─→ CHILD: "Comment Progresser Plus Vite à la Guitare ?" (H1)
```

---

## Règles Linking

### 1. PARENT vers CHILD

**Placement** : Après H2 correspondant, dans paragraphe intro section

**Format** :
```html
<h2>Choisir sa première guitare</h2>

<p>Le choix de votre première guitare est déterminant pour votre
motivation. Une guitare inadaptée peut décourager les débutants
dès les premières semaines.

Pour approfondir ce choix crucial, nous avons créé un guide détaillé :
<a href="/quelle-guitare-pour-debuter/">Quelle guitare pour débuter ?</a>

Ce guide couvre tous les aspects : taille, matériel, budget, etc.</p>
```

**Ancre** : Descriptive, reprend H1 du CHILD

```
✅ "Quelle guitare pour débuter ?" (descriptif)
✅ "Notre guide détaillé sur le choix instrumentaux" (contextuel)
❌ "Cliquez ici" (générique)
❌ "lien" (vide)
```

### 2. CHILD vers PARENT

**Placement** : Introduction (150 premiers mots)

**Format** :
```html
<p>Cet article fait partie de notre
<a href="/apprendre-guitare-guide-complet/">Guide Complet
pour Apprendre la Guitare</a>, qui couvre tous les aspects
de l'apprentissage débutant : choix instrument, accords,
solfège, et progression.</p>
```

**Ancre** : Mentionner le guide complet, contextuelle

```
✅ "Guide Complet pour Apprendre la Guitare" (titre descriptif)
✅ "notre guide d'apprentissage complet" (contexte)
❌ "ici" (generic)
❌ "MyMusicTeacher" (auteur, pas pertinent)
```

### 3. CHILD vers CHILD (Siblings)

**Placement** : Pertinent dans corps ou fin article, max 1 lien par H2

**Format** :
```html
<p>Maintenant que vous avez choisi votre guitare, l'étape suivante
est maîtriser <a href="/5-accords-guitare-essentiels/">
les 5 accords essentiels</a> pour jouer vos premiers morceaux.</p>
```

**Contexte** : Progression naturelle (A → B → C)

```
✅ Progression logique : "Après X, apprenez Y"
✅ Max 1 lien sibling par section (H2)
✅ Total max 3-4 liens internes par article
```

---

## Validation Cocon lors du Refresh

### Checklist AVANT Publication

- [ ] **Liens PARENT→CHILD existent** et fonctionnels
- [ ] **Liens CHILD→PARENT existent** (au moins 1 par CHILD)
- [ ] **Cohérence H2 PARENT = H1 CHILD** respectée exactement
- [ ] **Ancres descriptives** (pas "cliquez ici", pas "lien")
- [ ] **Liens internes préservés** depuis version précédente
- [ ] **Pas de broken links** (URLs valides, fonctionnelles)
- [ ] **URLs slugs cohérents** (H2 parent ≈ slug CHILD)

### Scénario : Détection Incohérence

**Avant refresh** :
```
PARENT H2: "Apprendre les accords"
CHILD H1: "5 Accords Guitare Essentiels"
Lien: /5-accords-guitare/
```

**Après refresh (changement détecté)** :
```
PARENT H2: "Maîtriser les bases des accords"  ❌ Incohérence
CHILD H1: "5 Accords Guitare Essentiels"
Lien: /5-accords-guitare/
```

**Action** :
1. Signaler dans rapport audit
2. Corriger H2 parent pour cohérence
3. OU corriger H1 child si préféré
4. Ne jamais cacher l'incohérence

---

## Cas d'Étude 1 : Cocon Éducation (Enseigna)

### Structure

```
PARENT: "Guide Complet Soutien Scolaire 2026"
├─ H2: "Avis Superprof (test complet)"
│    └─→ CHILD: "Avis Superprof 2026 : Test Complet"
│
├─ H2: "Académomia vs Superprof : comparatif"
│    └─→ CHILD: "Acadomia vs Superprof : Lequel Choisir ?"
│
├─ H2: "Cours à domicile vs en ligne"
│    └─→ CHILD: "Cours Particuliers : À Domicile ou En Ligne ?"
│
└─ H2: "Tarifs CESU : comprendre le calcul"
     └─→ CHILD: "Calcul CESU : Votre Coût Réel Famille"
```

### Linking Pattern

**PARENT (Guide Complet)** → Chaque H2 lien vers CHILD correspondant :

```html
<h2>Avis Superprof (test complet)</h2>

<p>Superprof est la plus grande plateforme française avec 800k
professeurs. Nous avons testé pendant 3 mois avec différents
profils d'élèves.

Résultats détaillés :
<a href="/avis-superprof-2026/">Avis Superprof 2026 : Test Complet</a>
</p>
```

**CHILD (Avis Superprof)** → Lien retour + liens siblings :

```html
<p>Cet avis fait partie de notre
<a href="/guide-soutien-scolaire-2026/">Guide Complet Soutien Scolaire</a>,
qui compare les meilleures plateformes.</p>

<!-- En fin d'article -->
<p>Pour comparer Superprof vs ses concurrents, voir aussi notre
<a href="/acadomia-vs-superprof/">comparatif Acadomia vs Superprof</a>.</p>
```

---

## Cas d'Étude 2 : Cocon Orientation (EducationetDevenir)

### Structure

```
PARENT: "Orientation Post-Bac 2026 : Guide Complet"
├─ H2: "Licence vs Bachelor : différences"
│    └─→ CHILD: "Licence ou Bachelor : Lequel Choisir ?"
│
├─ H2: "Les filières en demande 2026"
│    └─→ CHILD: "Filières Porteuses 2026 : Quels Débouchés ?"
│
├─ H2: "Salaires et insertion par métier"
│    └─→ CHILD: "Débouchés Informatique : Métiers et Salaires 2026"
│
└─ H2: "Préparer ton choix d'orientation"
     └─→ CHILD: "Bien Préparer Son Choix d'Orientation Post-Bac"
```

### Challenge : Nombreux CONCURRENTs CHILDS

**Pattern** : Quand PARENT a 10+ H2 (trop pour tous CHILD) :
- Garder seulement H2 les plus populaires comme liens
- Autres H2 = contenu purement informatif (pas liens)
- Éviter surcharger PARENT avec 10+ liens (UX dégradée)

---

## Anti-Patterns Cocon

### ❌ Incohérence H2/H1

```
PARENT H2: "Apprendre les accords"
CHILD H1: "Accords Guitare : Les 5 Essentiels"
→ Léger mismatch : reformuler H2 parent pour exact match
```

**Correction** :
```
PARENT H2: "Les 5 Accords Guitare Essentiels"  ✅ Exact match
CHILD H1: "Les 5 Accords Guitare Essentiels"   ✅ Exact match
```

### ❌ Liens Cassés

```
PARENT lien vers /old-url/
Mais CHILD a changé de slug → /nouveau-url/
→ Broken link = perte ranking + UX mauvaise
```

**Vérification** :
```bash
# Tester tous liens PARENT→CHILD
curl -I https://site.fr/new-url/  # 200 OK ?
```

### ❌ Orphaned Children

```
CHILD existe mais PARENT lien vers lui n'existe plus
→ CHILD devient orphelin, perd context signal, ranking baisse
```

**Règle** : Chaque CHILD doit avoir minimum 1 lien PARENT

### ❌ Cycles

```
PARENT A → CHILD B
CHILD B → PARENT A  ✅ OK (normal)

Mais CHILD B → CHILD C, CHILD C → PARENT A
→ Trop complexe, simplifié avec siblings uniquement
```

---

## Migration Cocon lors Refresh

**Si changement structure H2** :

1. **Identifier** : Quel H2 est devenu orphelin ?
2. **Décider** : Garder H2 ou créer nouveau CHILD ?
3. **Implémenter** : Ajuster liens cohérence
4. **Valider** : Tous liens fonctionnels post-refresh

**Exemple** :

```
AVANT refresh:
PARENT H2: "Apprendre les accords" → /5-accords.html
CHILD H1: "Les 5 Accords Guitare"

APRÈS refresh (reformulation H2):
PARENT H2: "Maîtriser les 5 accords de base" → /5-accords.html
CHILD H1: "Les 5 Accords Guitare"
→ TOUJOURS vérifier cohérence H2 = H1
```

---

*Version 2.0 - Février 2026*
