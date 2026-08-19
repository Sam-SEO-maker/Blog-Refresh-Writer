# Semantic density: occurrence-based model (SOSEO / DSEO)

Reference loaded on demand from `edito-refresh`. **Never reason in
"density %"**: reason in coverage + occurrences.

## Principle: two axes

1. **Coverage (BREADTH)**: use as many terms of the semantic field as possible. TOP 3 articles cover ~90% of the relevant terms.
2. **Moderation (DEPTH)**: do not repeat the same terms excessively.

The common mistake is NOT using too many different terms; it is
**repeating the same 5-6 terms too often**. Aim for breadth, not depth.

## Repetition caps (article of ~1800 words)

| Element | Limit |
|---------|--------|
| Main keyword (exact match) | **3-6 occurrences** (H1 + intro + 1-2 H2s + conclusion) |
| Top 10 important topic terms | 2-5 occurrences each, distributed |
| Other semantic-field terms | 1-3 occurrences each |
| Spacing | not the same term in 2 consecutive paragraphs |

## Mandatory synonymy rule

Any term appearing **3 times or more** → replaced by a synonym/paraphrase
in ≥ 50% of its occurrences. French content examples:
- « musculation » → « renforcement musculaire », « travail en salle »
- « coach » → « entraîneur », « préparateur physique »
- « séance » → « session », « créneau », « entraînement »

## SOSEO / DSEO target (YourTextGuru)

The target is **variable: it depends on each query's SERP**, never on a
uniform threshold. The YTG guide provides the competitors' average scores
(`top3_soseo`/`top3_dseo` and `top10_soseo`/`top10_dseo`); the rule:

| Metric | Rule vs TOP 3 average | Rule vs TOP 10 average |
|----------|------------------------|--------------------------|
| **SOSEO** (coverage) | article **> average** (e.g. average 60% → aim for > 60%) | article **> average** |
| **DSEO** (danger) | article **strictly < average** (e.g. average 5% → stay < 5%) | article **strictly < average** |

Beat the average, do not blow past it: an article at 116% SOSEO / 37% DSEO is
unusable (over-optimisation). Exceeding the SOSEO average by a few points
is enough; the DSEO must always stay below both averages.

## The target is a range: read the guide's `Recommended score`

The YTG guide exposes `target_SOSEO_min/max` and `target_DSEO_min/max` — the
**green zone** of its interface. Prefer them to the competitors' averages,
which a few non-editorial results are enough to distort: measured on
2026-08-14 for « majorée et minorée », 4 of the 9 SERP results (3 YouTube
videos + 1 text-less page) scored 0/0 and dragged the DSEO target down to 10.3
where YTG recommended **0-27**.

The SOSEO has a **maximum**, not just a floor. Which fix applies depends on
where it sits:

| SOSEO | DSEO | Fix |
|---|---|---|
| **above max** | any | **PRUNE** — cut redundancy; both scores drop together |
| inside range | above max | **REWRITE at constant volume** (below) |
| **below min** | inside | **ENRICH** — add the missing terms |

Pruning is not amputating: you cut repetitions, redundant examples, digressions
and reformulations that add nothing — never a sourced fact, a statistic, a
quote, a table, an image or a link (Golden Rule).

## Fixing a too-high DSEO when the SOSEO is inside its range

Here the coverage is right and only the density overflows. The instinct to cut
text is wrong in this case: cutting removes concepts, so the SOSEO falls under
its floor and you trade one error for the other.

**Both scores follow length, but they do not follow *repetition* the same way.**
SOSEO counts how many distinct terms of the field you cover; DSEO counts how
heavily you lean on the same ones. So the lever is **rewriting at constant
volume**, exactly what a human editor does:

1. **Reformulate** the sentence rather than delete it — same fact, different
   wording.
2. **Substitute synonyms** for the terms YTG flags `red` (`over_optimized_terms`
   in the QC result: that list IS the worklist).
3. **Pronominalise** the 2nd and 3rd mentions inside a paragraph
   (« la suite majorée » → « elle », « cette dernière »).
4. **Promote hyperonyms/hyponyms**: « majorant » → « cette borne »,
   « ce réel », « la valeur qui plafonne la suite ».
5. **Check consistency and harmonise** across sections afterwards: a synonym
   introduced in §3 must not contradict the definition given in §1, and a term
   defined once must stay stable where it is the technical object of the
   sentence.

Not a single sourced fact, statistic, quote, table or image may disappear in
this pass (Golden Rule). Word count stays within ±5%.

**Never touch a definition sentence.** In « un majorant est un réel M tel
que… », the word is the object being defined: replacing it there breaks the
teaching. Substitute in the *commentary* sentences, never in the definition,
the theorem statement or the exercise wording.

### The SOSEO target can be partly unreachable — do not chase it blindly

`under_optimized_terms` sometimes contains **LaTeX macros** (`mathbb`, `dfrac`,
`overrightarrow`, `geqslant`, `displaystyle`, `sqrt`, `text`) because the
competitors ship raw LaTeX. Measured on 2026-08-14: 3 of 5 scientific articles
were asked for such terms. This site does **not** render LaTeX — see the
project rule on Unicode in `<code>`. Adding them to chase the SOSEO would
reintroduce the exact rendering bug the refresh removes.

Ignore those terms. If the remaining SOSEO gap is made only of LaTeX artefacts,
the article is done: report the gap, do not close it.

Likewise a **DSEO target ≤ 3%** is an artefact, not an editorial goal. Those
1-3% targets came from the SERP-average fallback, which non-editorial results
drag toward zero; the guide's own `Recommended score` is far wider (0-24 to
0-32 on the same articles). If a target that low still shows up — meaning the
guide exposed no range and the fallback applied — report it and stop; do not
degrade prose to reach it.

## ❌ Forbidden / ✅ Correct

Forbidden: stacking 3+ technical terms in one sentence; repeating a term in 2
consecutive paragraphs; vocabulary "catalogue" sentences; forcing a technical
term where a common word suffices; concentrating the vocabulary in one section.

Correct: specialised vocabulary when it adds precision; paraphrases rather than
repetitions; uniform distribution; write for the reader first; let some
paragraphs "breathe" in natural prose.

## Example

French content example:

```
❌ SUROPTIMISÉ :
"Le squat, exercice polyarticulaire d'hypertrophie, sollicite les quadriceps...
La charge progressive en squat permet l'hypertrophie des quadriceps..."
→ 3x "squat", 2x "hypertrophie", 2x "quadriceps" en 3 phrases

✅ OPTIMAL :
"Le squat sollicite simultanément plusieurs groupes musculaires majeurs :
quadriceps, fessiers et ischio-jambiers. C'est un mouvement fondamental pour
développer la force du bas du corps. En augmentant progressivement la charge,
vous stimulez une croissance musculaire durable."
→ 1x "squat", termes variés, lecture fluide
```

## Example: rewriting at constant volume (DSEO down, SOSEO held)

Real case, `volume-fraction-resolution` (SOSEO 135/42, DSEO 61/10). YTG flags
`majorant`, `majorée`, `minorée`, `bornée`, `suites` as `red`.

```
❌ AVANT (5 occurrences des termes rouges en 3 phrases)
"Une suite est majorée si elle admet un majorant. Un majorant d'une suite
est un réel M tel que tous les termes lui sont inférieurs. Si M majore la
suite, alors tout réel plus grand majore aussi la suite."

✅ APRÈS (2 occurrences, même longueur, définition intacte)
"Une suite est majorée si elle admet un majorant, c'est-à-dire un réel M tel
que tous ses termes lui restent inférieurs ou égaux. Dès qu'un tel plafond
existe, n'importe quelle valeur au-dessus joue le même rôle : on en exhibe
un, on ne cherche jamais « le » bon."
```

The definition keeps its technical term (it is the object being defined); the
commentary switches to « plafond », « valeur », « tel ». Same facts, same
length, DSEO down, SOSEO untouched.

*Canonical reference for the SOSEO/DSEO model (migrated from the former STYLE_GUIDE.md §11,
deleted). Cited by the full_refresh and semantic_reorientation strategies.*
