# E-E-A-T : framework détaillé (Experience, Expertise, Authoritativeness, Trust)

Référence chargée à la demande depuis `edito-refresh`. Les 4 piliers avec paires
❌/✅ et signaux. **Principe clé** : la Confiance (Trust) est l'élément le plus
important, sans confiance, les autres signaux sont insuffisants.

## 1. Experience (expérience pratique)

- ❌ « Acadomia est une plateforme de soutien scolaire. »
- ✅ « Après avoir testé Acadomia pendant 3 mois avec ma fille en 4ème, voici notre retour détaillé… L'enseignante a d'abord évalué le niveau, puis proposé un plan personnalisé. »

Signaux : détails concrets spécifiques, nuances que seul un praticien connaîtrait, vocabulaire de terrain, captures/photos réelles si disponibles.

## 2. Expertise (compétence technique)

- ❌ « Beaucoup d'élèves prennent des cours particuliers. »
- ✅ « Selon le DEPP (ministère de l'Éducation), 40% des collégiens bénéficient de soutien scolaire (2025). Le marché représente 2,5 milliards € annuels. »

Signaux : sources académiques (CNRS, INSERM, DEPP), données < 2 ans, vocabulaire technique expliqué, experts reconnus, études méthodologiquement saines.

## 3. Authoritativeness (autorité)

- ❌ « Un expert recommande cette plateforme. »
- ✅ « Dr. Marie Dupont, directrice du laboratoire de psychologie de l'apprentissage à la Sorbonne et auteure de "Apprendre Efficacement" (Dunod, 2023), recommande… »

Signaux : auteur avec credentials complets, titres académiques/professionnels, affiliations reconnues, publications datées, citations de sources primaires, liens vers sites d'autorité.

## 4. Trustworthiness (fiabilité)

Signaux : disclaimers transparents, méthodologie expliquée, dates visibles, sources vérifiables avec liens, absence de conflits d'intérêt (ou transparence totale).

> **Note site** : la **déclaration d'indépendance éditoriale** est **interdite sur
> Enseigna** (voir sa skill), ne pas l'inclure. Elle n'est prescrite pour aucun
> site actuel par défaut.

## Sources institutionnelles (principe transverse)

**Minimum : ≥ 3 sources institutionnelles citées avec lien** (uniforme, tous sites).

**Types de domaines à viser** (valable quel que soit le site) :
- **Gouvernemental / officiel** : ministères, agences publiques, autorités de régulation.
- **Académique** : archives ouvertes, revues à comité de lecture, presses universitaires.
- **Statistique** : institut national de statistiques, organismes internationaux (OCDE…).

**Les domaines concrets sont un savoir par site, pas transverse** : ils vivent
dans l'annuaire du site `sites/<site-slug>/sources/authority-map.md` (par matière + socle
transverse), consommé au tier 1 de la skill `recherche-sources`. Ne pas maintenir de
liste de domaines ici. Domaines interdits (concurrents, agrégateurs) :
`recherche-sources/references/blacklisted-domains.md`.

**Jamais de lien vers Wikipédia** (tous sites) : Wikipédia agrège des sources primaires
sans être lui-même une autorité E-E-A-T. Remonter à la source qu'il cite (étude, texte
officiel, institution) et lier celle-ci à la place.

## YMYL (Your Money or Your Life)

Sujets impactant santé, finances ou bonheur du lecteur → niveau E-E-A-T élevé requis.
- **Éducation** : sources institutionnelles, données officielles, expertise pédagogique démontrée.
- **Finance/tarifs (Enseigna)** : transparence des prix, comparaisons objectives.

## Auteur et bio : géré par WordPress, PAS dans le HTML

L'auteur, sa bio et ses credentials sont gérés par le **profil WordPress**, hors
du corps de l'article. **Ne pas insérer de bloc « À propos de l'auteur » dans le
HTML généré.** (Le nom d'auteur reste un fait E-E-A-T, simplement porté par le CMS.)

## Grille d'audit E-E-A-T (0-100) : pour évaluer un article existant

Experience /25 · Expertise /25 · Authority /25 · Trust /25.
- < 40 : réécriture totale · 40-60 : réécriture partielle (enrichissement E-E-A-T)
- 60-80 : mise à jour ciblée · > 80 : refresh léger (stats, dates)

*Source : fusion de l'ancien EEAT_GUIDE.md (savoir migré en references). Arbitrages
appliqués : min 3 sources uniforme (C10), bio hors-HTML (C11), indépendance interdite (C12).*
