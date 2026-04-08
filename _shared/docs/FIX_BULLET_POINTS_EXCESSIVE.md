# Fix: Bullet Points Excessifs dans Articles Générés

**Date**: 2026-02-18
**Problème**: Articles générés en mode "annuaire" avec dizaines de listes à puces
**Solution**: Renforcement des règles anti-bullet-points dans les prompts

---

## Problème Constaté

### Exemple Article Problématique

**URL**: `https://coachsportlyon.fr/exercices-musculation-squat/`
**Fichier**: `_shared/outputs/coachsportlyon.fr/https_coachsportlyon_fr_exercices_musculation_squat_refreshed.html`

**Symptômes** :
- Dizaines de listes à puces (> 50 bullet points)
- Quasi-aucun paragraphe narratif
- Style "catalogue technique" au lieu de contenu éditorial
- Lecture fragmentée et robotique

### Exemple de Contenu Généré (AVANT)

```markdown
## Muscles sollicités

Le squat sollicite :
- Quadriceps
- Fessiers
- Ischio-jambiers
- Mollets
- Abdominaux
- Érecteurs du rachis
- Adducteurs

## Erreurs courantes

**Erreur 1 : Genoux qui dépassent**
- Problème : Stress genoux
- Correction : Hanches vers l'arrière

**Erreur 2 : Dos arrondi**
- Problème : Blessure colonne
- Correction : Abdos contractés

[... 6+ erreurs avec même structure]
```

**Résultat** : Article illisible, style annuaire, pas engageant.

---

## Cause Racine

### Architecture Prompts

Les prompts étaient composés en 4 niveaux :
1. **Category** (`_shared/prompts/categories/sport/sport.md`)
2. **Strategy** (MANQUANT pour FULL_REFRESH - utilisait instruction hardcodée courte)
3. **Site** (`_shared/prompts/sites/coachsportlyon.md`)
4. **Template** (optionnel)

**Problème** : AUCUN de ces niveaux ne forçait explicitement l'utilisation de paragraphes narratifs au lieu de listes.

Le STYLE_GUIDE.md contenait la règle (section 7) mais elle n'était pas injectée dans les prompts de génération.

---

## Solution Implémentée

### Modifications Fichiers

#### 1. `_shared/prompts/sites/coachsportlyon.md`

**Ajout section complète** :
```markdown
## ⚠️ FORMAT RÉDACTIONNEL (CRITIQUE)

### INTERDICTION ABSOLUE : Listes à puces excessives

❌ Articles annuaire = REJET AUTOMATIQUE
✅ Rédaction narrative OBLIGATOIRE

### Règles strictes

1. Paragraphe = minimum 3 phrases
2. Listes autorisées uniquement pour : énumérations brèves (3-5 items), contre-indications, FAQ
3. Tout le reste = prose narrative
4. Transitions fluides entre sections
```

**Exemples concrets** : AVANT (interdit) vs APRÈS (attendu)

#### 2. `_shared/prompts/strategies/full_refresh.md` (NOUVEAU)

**Création fichier complet** avec :
- Règle d'or préservation assets
- Format rédactionnel critique (anti-bullet-points)
- Exemples transformation AVANT/APRÈS
- Processus détaillé section par section
- Checklist validation obligatoire

**Points clés** :
- "Maximum 2-3 listes par article (hors FAQ)"
- "Paragraphes fluides de 3-5 phrases minimum"
- Exemples concrets de transformation liste → paragraphe narratif

#### 3. `_shared/prompts/categories/sport/sport.md`

**Ajout section** :
```markdown
## ⚠️ Format Rédactionnel OBLIGATOIRE

RÈGLE CRITIQUE : Rédaction narrative, PAS style annuaire

✅ Paragraphes fluides de 3-5 phrases
❌ Dizaines de bullet points (max 2-3 listes/article)
```

---

## Format Attendu Désormais

### Exemple de Contenu Généré (APRÈS)

```markdown
## Muscles sollicités pendant le squat

Le squat est un exercice polyarticulaire qui recrute simultanément plusieurs
groupes musculaires majeurs. Les quadriceps, situés à l'avant des cuisses,
assurent l'extension du genou et sont particulièrement sollicités lors de la
phase de remontée. Les fessiers (grand, moyen et petit glutéal) interviennent
pour l'extension de la hanche, surtout en fin de mouvement.

Les ischio-jambiers, à l'arrière des cuisses, jouent un rôle stabilisateur
important en contrôlant la descente et en protégeant l'articulation du genou.
Les adducteurs (muscles internes des cuisses) contribuent à maintenir la
stabilité latérale durant tout le mouvement.

Au-delà des jambes, le squat engage fortement la ceinture abdominale et les
érecteurs du rachis (muscles profonds du dos). Cette activation du tronc est
essentielle pour maintenir une colonne vertébrale en position neutre et prévenir
les blessures.

## Erreurs techniques fréquentes et corrections

Identifier et corriger ces erreurs est essentiel pour progresser en toute sécurité.
La première erreur courante concerne les genoux qui dépassent excessivement les
orteils. Ce positionnement crée une pression excessive sur l'articulation du genou.
Pour corriger cela, initiez le mouvement par les hanches en les poussant vers
l'arrière avant de fléchir les genoux, comme si vous vous asseyiez sur une chaise.

Le dos arrondi ou l'hyperextension lombaire représente la deuxième erreur majeure.
Cette position expose la colonne vertébrale à des risques de blessure importants.
Maintenez une courbure lombaire neutre en contractant les abdominaux, en gardant
la poitrine ouverte et en fixant un point droit devant vous.

[... paragraphes narratifs pour autres erreurs]
```

**Résultat** : Article fluide, engageant, professionnel, facile à lire.

---

## Règles de Validation

### Checklist Post-Génération

Avant d'accepter un article généré, vérifier :

- [ ] **Maximum 2-3 listes** dans tout l'article (hors FAQ et contre-indications)
- [ ] **Chaque liste : maximum 5 items**
- [ ] **Tous les paragraphes = minimum 3 phrases**
- [ ] **Transitions fluides** entre sections
- [ ] **Style narratif** dominant (pas catalogue)
- [ ] **Assets préservés** (count APRÈS ≥ count AVANT)

### Quand les Listes SONT Autorisées

✅ **Contextes légitimes** :
1. **FAQ** : Questions-réponses (structure naturellement list-based)
2. **Contre-indications** : Encadré sécurité (YMYL - clarté prime)
3. **Énumérations brèves** : 3-5 items maximum, contexte justifié
4. **Checklists pratiques** : Validation, échauffement (si pertinent)

❌ **Contextes interdits** :
- Sections principales (Bénéfices, Technique, Erreurs, etc.)
- Descriptions de concepts
- Explications complexes
- Tout ce qui peut être narratif

---

## Impact Attendu

### Avant Fix

- Articles "annuaire" difficiles à lire
- Bounce rate élevé
- Temps sur page faible
- Impression non-professionnelle
- SEO dégradé (contenu fragmenté)

### Après Fix

- Articles narratifs engageants
- Lecture fluide et agréable
- Temps sur page augmenté
- Qualité éditoriale professionnelle
- SEO optimisé (contenu riche et contextualisé)

---

## Test de Validation

### Commande Test

```bash
# Regénérer l'article squat avec nouveaux prompts
python srw.py refresh-url \
  --url "https://coachsportlyon.fr/exercices-musculation-squat/" \
  --blog-id coachsportlyon.fr \
  --action FULL_REFRESH
```

### Critères de Succès

1. **Compte bullet points** : Moins de 15 items au total (hors FAQ)
2. **Ratio paragraphes/listes** : > 80% paragraphes narratifs
3. **Longueur paragraphes** : Minimum 3 phrases chacun
4. **Transitions** : Présentes entre chaque section
5. **Lisibilité** : Article agréable à lire d'une traite

### Points de Vérification

```bash
# Compter les balises <ul> et <li> dans l'output
grep -o "<ul>" output.html | wc -l  # Doit être ≤ 3
grep -o "<li>" output.html | wc -l  # Doit être ≤ 15

# Compter les paragraphes <p>
grep -o "<p>" output.html | wc -l  # Doit être > 30
```

---

## Prochaines Étapes

1. **Tester génération** avec article problématique (squat)
2. **Valider résultat** avec checklist
3. **Appliquer à d'autres blogs** si succès (moments-yoga, etc.)
4. **Documenter dans MEMORY.md** si pattern récurrent

---

## Fichiers Modifiés

- ✅ `_shared/prompts/sites/coachsportlyon.md` (section FORMAT RÉDACTIONNEL ajoutée)
- ✅ `_shared/prompts/strategies/full_refresh.md` (fichier créé, 350+ lignes)
- ✅ `_shared/prompts/categories/sport/sport.md` (section Format Rédactionnel ajoutée)

## Fichiers de Référence

- 📖 `_shared/docs/STYLE_GUIDE.md` (section 7 : Bullet Points Excessifs)
- 📖 `CLAUDE.md` (règles anti-patterns)

---

*Fix appliqué le 2026-02-18*
*Auteur : Claude Opus 4.6*
*Contexte : Correction prompt suite article "annuaire" squat*
