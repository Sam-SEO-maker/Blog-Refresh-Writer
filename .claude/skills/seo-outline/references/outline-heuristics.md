# Heuristiques d'outline — cas particuliers de subdivision

Détail des arbitrages du `SKILL.md` (chargé à la demande). L'algorithme de base :
compter les mots de paragraphe **prévus** par section, appliquer les seuils.

## Subdivision d'un H2 en H3

```
mots_prevus(H2) < 150   → 0 H3 (contenu direct sous le H2)
150 ≤ mots < ~400       → 2 à 3 H3
~400 ≤ mots ≤ ~600      → 3 à 4 H3
mots > ~600             → scinder en 2 H2 (chacun ré-évalué)
```

- Jamais **1 seul** H3 : soit on reste à 0 (contenu direct), soit ≥ 2. Un H3 isolé
  signale un découpage arbitraire — le fondre dans le corps du H2.
- Jamais **plus de 4** H3 : au-delà, le H2 traite en réalité deux sujets → le
  scinder. Deux H2 de 3 H3 valent mieux qu'un H2 de 6 H3.

## H2 à la limite (≈ 150 mots)

Zone grise 130-170 mots : trancher par la **cohésion**, pas par le compteur.

- Le contenu répond à **une** question → garder en H2 sans H3, même à 160 mots.
- Le contenu couvre **deux angles distincts** (ex. « avantages » + « limites ») →
  subdiviser en 2 H3 même à 140 mots. La subdivision suit le sens, le seuil de 150
  n'est qu'un déclencheur par défaut.

## PAA multiples sous un même H2

- 2-3 PAA proches (même intention) → un H2 avec un H3 par PAA (réponse directe en
  tête de chaque H3). Respecte le plancher de 2 H3.
- 1 seule PAA → H2 sans H3, la réponse directe ouvre le H2.
- PAA hétérogènes → ne pas les forcer sous un même H2 ; répartir sur plusieurs H2.

## Arbitrage 3 vs 4 H3

- Préférer **3 H3** équilibrés à 4 déséquilibrés (un H3 famélique à 30 mots = à
  fusionner avec un voisin).
- Passer à 4 H3 seulement si chacun tient ≥ ~80 mots et couvre un angle propre.

## Titres interrogatifs

- Ne transformer en question que ce qui **est** une question (souvent une PAA reprise
  telle quelle) : « Combien coûte un cours particulier ? ».
- Un titre déclaratif reste déclaratif, sans `?` : « Le tarif moyen d'un cours ».
- Ne pas empiler les questions : alterner interrogatifs et déclaratifs pour le rythme.
