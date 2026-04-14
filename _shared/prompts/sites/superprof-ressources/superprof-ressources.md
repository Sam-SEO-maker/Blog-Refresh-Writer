# Site Override : Superprof Ressources FR

**Domain** : https://www.superprof.fr/ressources/
**Language** : Français
**YMYL Level** : Low
**Tone profile** : Naturel, plutôt informel, encourageant, respectueux

> ⚠️ **TODO Tone & Voice définitif** : en attente de la Product Owner Manager. En attendant, appliquer strictement le Guide 1 (section "Our Voice & Tone").

## Règles éditoriales (sources)

Toutes les règles d'écriture, SEO, formatage et refresh sont définies dans les 3 guides officiels Superprof, à charger AVANT toute génération :

1. [Guide 1 — Blog Writing Foundations](./superprof-ressources/guide-1-blog-writing-foundations.md)
   *Brand values, voice & tone, public, qualité, AI guidelines, images*
2. [Guide 2 — Blog Writing Reference](./superprof-ressources/guide-2-blog-writing-reference.md)
   *SEO elements, linking & anchor text, titres, images, blocs WordPress, formatage, checklist publication*
3. [Guide 3 — Working with Refreshes](./superprof-ressources/guide-3-working-with-refreshes.md)
   *Process refresh, règles critiques, checklist refresh, exemples*

Le pipeline de prompt composer DOIT injecter le contenu intégral de ces 3 guides (ou au minimum Guide 1 + Guide 3 pour les refresh) dans le prompt de génération.

## Règles non-négociables (résumé exécutif)

### Identité de marque
- ✅ **Superprof** (un seul mot, S majuscule, p minuscule)
- ❌ JAMAIS : "Super Prof", "SuperProf", "SP"
- Superprof n'est ni "il" ni "elle" — pas de pronom personnel

### Voice & Tone
- Naturel, plutôt informel, conversationnel sans être négligé
- **Formuler positivement** (opportunité > manque/échec)
- Inspirer, ne pas décourager
- Phrases courtes (< 20 mots), une idée par phrase, voix active
- Paragraphes de **3 à 5 phrases** (jamais de phrases flottantes)
- Intros courtes (1-2 paragraphes max), directes et engageantes

### Anchor text & linking (CRITIQUE SEO)
- **JAMAIS** de money keywords en anchor text vers un blog article
- Liens blog→blog : warm/cold keywords uniquement
- Liens blog→landing (`/lessons/`) : money keywords autorisés
- Cf. Guide 2 — section "Linking" pour les règles complètes

### AI usage
- ✅ Inspiration, structure, titres, CTA, grammaire
- ❌ JAMAIS de copier-coller direct de texte généré par IA
- La voix et le jugement restent humains. Audits aléatoires de plagiat/AI-detection.

### Images
- Sens > esthétique. Chaque image doit ajouter quelque chose à la compréhension.
- Préférer Unsplash et photos authentiques aux stocks caricaturaux
- Légendes contextuelles (lieu, sujet, photographe le cas échéant)

### Refresh (Guide 3)
- Préserver l'intention originale et l'URL
- Mettre à jour stats, exemples, structure, visuels selon le brief
- Respecter les blocs Gutenberg obligatoires (cf. Guide 2)
- Utiliser le bon éditeur WordPress (cf. Guide 3 — "Critical Rules")

## Anti-patterns à proscrire

- ❌ Sujets controversés / positions politiques
- ❌ Langage sensationnel ("incredible", "amazing", "révolutionnaire")
- ❌ Tangentes hors-sujet
- ❌ Références/stats non valables pour le marché FR
- ❌ Bold sur des phrases entières (réservé aux termes-clés)
- ❌ Money keywords en anchor text vers du blog
- ❌ Sentences flottantes hors paragraphes
