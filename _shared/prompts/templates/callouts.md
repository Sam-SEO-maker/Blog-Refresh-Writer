# Templates Callouts HTML

Encadrés et boîtes d'information pour articles WordPress.

---

## 1. CTA Superprof (VERT) - Avec Lien

**Placement** : Libre dans l'article, hors introduction

**Variante A : Accroche géographique (PRIORITAIRE pour landings ville)**

L'ancre est amenée par un contexte géographique naturel. Le lecteur comprend POURQUOI on parle de cette ville.

```html
<div style="background-color: #4caf50; padding: 20px; border-radius: 8px; margin: 25px 0;">
  <p style="color: white; margin: 0; font-weight: bold;">
    Vous souhaitez être accompagné par un professionnel ?
  </p>
  <p style="color: white; margin: 10px 0 0 0;">
    [Phrase d'accroche géographique contextuelle, voir exemples ci-dessous].
    Un <a href="[URL_EXACTE_DU_PROMPT]"
           style="color: #fff; text-decoration: underline; font-weight: bold;">
    [ANCRE_EXACTE_DU_PROMPT]
    </a> [suite naturelle de la phrase, 1-2 lignes max].
  </p>
</div>
```

**Exemples de phrases d'accroche géographique** (varier à chaque article) :

| Landing ville | Exemples d'accroche (choisir/adapter UN seul) |
|---|---|
| Paris | "La capitale regorge de professionnels expérimentés." / "En région parisienne, l'offre ne manque pas." |
| Lyon | "Du côté de Lyon, la communauté [discipline] est particulièrement active." / "Si vous êtes dans la région lyonnaise, vous trouverez facilement un accompagnement." |
| Marseille | "Dans le sud, et notamment à Marseille, la pratique [discipline] se développe." / "Vous êtes en région marseillaise ?" |
| Toulouse | "En région toulousaine ? L'offre de [discipline] s'est étoffée ces dernières années." |
| Nantes | "Du côté de Nantes, plusieurs professionnels proposent un accompagnement individuel." |
| Online | "Où que vous soyez en France, un accompagnement à distance reste une option efficace." / "Pas de professeur près de chez vous ?" |
| France (générique) | "Partout en France, il est possible de trouver un accompagnement adapté." / "De nombreux professionnels proposent leurs services à domicile ou en visio." |

**RÈGLE CLÉ** : la phrase d'accroche doit **justifier naturellement** la mention de la ville. Ne JAMAIS écrire "Un [ancre avec ville]" sans contexte géographique préalable.

**Variante B : Point de douleur + contexte**

```html
<div style="background-color: #4caf50; padding: 20px; border-radius: 8px; margin: 25px 0;">
  <p style="color: white; margin: 0; font-weight: bold;">
    [Problème concret abordé dans la section précédente] ?
  </p>
  <p style="color: white; margin: 10px 0 0 0;">
    [Phrase d'accroche géographique]. Un
    <a href="[URL_EXACTE_DU_PROMPT]"
       style="color: #fff; text-decoration: underline; font-weight: bold;">
    [ANCRE_EXACTE_DU_PROMPT]
    </a> peut vous aider à [bénéfice concret lié au H2 précédent, 1 ligne max].
  </p>
</div>
```

**Variante C : Constat terrain**

```html
<div style="background-color: #4caf50; padding: 20px; border-radius: 8px; margin: 25px 0;">
  <p style="color: white; margin: 0; font-weight: bold;">
    [Constat ou observation liée au sujet de l'article]
  </p>
  <p style="color: white; margin: 10px 0 0 0;">
    [Phrase d'accroche géographique ou générique].
    Les <a href="[URL_EXACTE_DU_PROMPT]"
            style="color: #fff; text-decoration: underline; font-weight: bold;">
    [ANCRE_EXACTE_DU_PROMPT]</a>
    le constatent régulièrement : [insight concret, 1 ligne].
  </p>
</div>
```

**Règles CTA Superprof** :

- 0 ou 1 CTA par article, selon pertinence du sujet
- Placement libre hors introduction
- Toujours avec lien
- Alternez variantes A/B/C (pas répétition structurelle)
- Ancre naturelle (jamais "Cliquez ici")
- **URL et ancre** : fournies dynamiquement par le système de rotation (`SuperprofRotator`). Le prompt de génération contient la directive exacte (URL + ancre + contexte géographique). Ne pas inventer d'URL ni d'ancre — utiliser celles du prompt.
- **Contexte géographique OBLIGATOIRE** : si l'ancre contient une ville (Lyon, Paris, Marseille...), la phrase DOIT amener cette ville naturellement AVANT le lien. Voir le tableau d'accroches géographiques ci-dessus.
- Si aucune directive n'est présente dans le prompt, fallback : `https://www.superprof.fr/cours/[matiere]/france/`

---

## 2. Bon Réflexe (JAUNE) - Sans Lien

**Placement** : Libre dans l'article, hors introduction

**Format Basique** :

```html
<div style="background-color: #fff9e6; padding: 20px; border-radius: 8px;
            border-left: 4px solid #ffc107; margin: 25px 0;">
  <p style="margin: 0; font-weight: bold;">💡 Bon réflexe</p>
  <p style="margin: 10px 0 0 0;">
    [Conseil actionnable et contextualisé à la section précédente, 2-3 phrases max]
  </p>
</div>
```

**Exemple : Article Guitare**

```html
<div style="background-color: #fff9e6; padding: 20px; border-radius: 8px;
            border-left: 4px solid #ffc107; margin: 25px 0;">
  <p style="margin: 0; font-weight: bold;">💡 Bon réflexe</p>
  <p style="margin: 10px 0 0 0;">
    N'ajustez pas la tension des cordes trop brutalement.
    Une petite torsion à la fois : votre guitare vous remerciera
    (et votre son sera plus stable).
  </p>
</div>
```

**Exemple : Article Orientation**

```html
<div style="background-color: #fff9e6; padding: 20px; border-radius: 8px;
            border-left: 4px solid #ffc107; margin: 25px 0;">
  <p style="margin: 0; font-weight: bold;">💡 Bon réflexe</p>
  <p style="margin: 10px 0 0 0;">
    Consultez les salons étudiants de votre région (janvier-mars).
    Vous y rencontrerez directement des écoles et des professionnels
    du secteur. C'est plus utile que 10 sites web.
  </p>
</div>
```

**Règles Bon Réflexe** :

- 0 à 3 par article, selon pertinence
- Sans lien (information pure)
- Conseil très contextualisé (pas générique)
- Plutôt court (2-3 phrases)
- Varier contenu entre articles (pas réutiliser même conseil)

---

## 3. Info Highlight (BLEU) - Pas d'Emoji

**Placement** : Statistic clé, donnée importante, mise en garde douce

**Format Standard** :

```html
<div style="background-color: #e8f4f8; padding: 20px; border-radius: 8px;
            border-left: 4px solid #1976d2; margin: 25px 0;">
  <p style="margin: 0;">
    <strong>[Information clé ou statistique]</strong>
  </p>
  <p style="margin: 10px 0 0 0;">
    [Développement ou contexte sur l'information]
  </p>
</div>
```

---

## 4. Disclaimer Sport/Santé (ORANGE) - YMYL Obligatoire

**Placement** : Voir le **site override** du blog concerné (`_shared/prompts/sites/{site_id}.md`).

**Blogs concernés** : **coachsportlyon.fr**, **moments-yoga.fr** (YMYL VERY HIGH)

**Format YMYL** :

```html
<div style="background-color: #fff3cd; border-left: 4px solid #ff9800; padding: 20px; margin-bottom: 30px;">
  <p style="margin: 0; font-weight: bold;">⚠️ Avertissement Santé</p>
  <p style="margin: 10px 0 0 0;">Avant de commencer tout programme d'entraînement ou d'exercice physique, consultez un professionnel de santé. Les informations présentées ici sont à but éducatif et ne remplacent en aucun cas un avis médical personnalisé.</p>
</div>
```

**⚠️ RÈGLES FORMAT** :
- **Utiliser `<p>` pour le titre** (JAMAIS `<h3>` ou autre heading)
- **Pas de Title Case** : écrire "Avant de commencer" ou "Avant de débuter", PAS "Avant de Commencer" ni "Avant de Débuter" (seul le premier mot prend une majuscule)
- **Titre unique par article** : créer un titre de disclaimer original et adapté au sujet de chaque blogpost (ne pas réutiliser le même titre générique partout)
- **Obligatoire pour blogs sport/santé** (coachsportlyon, moments-yoga)
- **Pas de lien** dans le disclaimer (info pure)
- **Ton neutre** et responsable

**Exemple : Article YMYL (Yoga)**

```html
<div style="background-color: #e8f4f8; padding: 20px; border-radius: 8px;
            border-left: 4px solid #1976d2; margin: 25px 0;">
  <p style="margin: 0;">
    <strong>À retenir :</strong> Le yoga réduit le cortisol
    (hormone stress) de 35% chez 75% des pratiquants (INSERM, 2024).
  </p>
  <p style="margin: 10px 0 0 0;">
    C'est un effet mesurable, pas cosmétique. Mais résultats varient
    selon condition physique et durée pratique.
  </p>
</div>
```

**Exemple : Article Orientation**

```html
<div style="background-color: #e8f4f8; padding: 20px; border-radius: 8px;
            border-left: 4px solid #1976d2; margin: 25px 0;">
  <p style="margin: 0;">
    <strong>Chiffre clé :</strong> 78% d'insertion professionnelle
    en 3 mois pour Licence Informatique (ONISEP, 2025).
  </p>
  <p style="margin: 10px 0 0 0;">
    C'est bien au-dessus de la moyenne nationale (65%).
    Mais attention : 22% gagnent moins de 2200€/mois première année.
  </p>
</div>
```

**Règles Info Highlight** :

- 0 à 2 par article, selon pertinence
- Chiffre/donnée chiffrée obligatoire
- Pas d'emoji (juste couleur pour saillance)
- Contexte chiffre en 2e paragraphe (pas juste stat brute)
- Source toujours incluse (date minimum)

---

## Récapitulatif Callouts

| Type | Couleur | Lien | Nombre | Placement |
|------|---------|------|--------|-----------|
| CTA Superprof | Vert | OUI | 0-1 | Libre, hors intro |
| Bon Réflexe | Jaune | NON | 0-3 | Libre, hors intro |
| Info Highlight | Bleu | NON | 0-2 | Libre, hors intro |

**Total** : 1 à 3 encadrés par article selon pertinence. Varier les types et placements entre articles.

---

## Note Importante : Responsive Design

Tous templates ci-dessus sont **inline CSS**. Pour mobile :

```html
<!-- Ajouter media query si style externe existe -->
@media (max-width: 600px) {
  div { padding: 15px !important; margin: 15px 0 !important; }
  a { display: block; margin-top: 10px; }
}
```

---

*Version 2.0 - Février 2026*
