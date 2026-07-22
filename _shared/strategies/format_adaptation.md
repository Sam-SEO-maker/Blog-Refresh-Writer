# FORMAT_ADAPTATION: Adapting to the SERP format

## When
The article's format ≠ the dominant SERP format (e.g. long guide → listicle,
article → FAQ, text → table).

## Scope
**Restructure** towards the dominant SERP format: change the STRUCTURE, not the substance.
Keep all the information and all the assets (no loss, no reduction).

## Strategy-specific delta: the 5 format templates

### 1. Listicle ("X methods", "Top Y")
H1 `[Number] [Topic] [Year]` → quick summary → one numbered H2 per item
(100-150 word description + bullets) → recap table → FAQ.

### 2. Guide / How-to ("How to", "Tutorial")
H1 `How to [Action]: [Year] Guide` → prerequisites (time, difficulty, materials) →
one H2 per sequential step (+ step image) → H2 "Common mistakes to avoid"
(mistake → solution) → FAQ.

### 3. Comparison / Versus ("vs", "best")
H1 `[A] vs [B]: [Year] Comparison` → direct verdict (1-2 sentences) → comparison
table by criterion → "[A] in detail" (H3 pros/cons) → same for [B] →
"Which one to choose?" (conditions per option) → FAQ.

### 4. Extended FAQ (SERP dominated by PAA)
H1 `[Topic]: answers to your questions` → short intro → H2 "Frequently asked questions"
→ one H3 per question (phrased like a Google search): direct answer in bold
+ 50-100 word development → complementary resources. Extended FAQ = more
questions than the default (the default count lives in `edito-refresh`).

### 5. Definition / Explanation ("What is")
H1 `What is [Topic]?` → definition in 1-2 sentences (featured snippet) →
"Full definition" → "How does it work?" → concrete examples →
pros/cons (table) → FAQ.

## Conversion rules

- **Guide → Listicle**: extract the key points, number them, add a recap table, keep the detail per point.
- **Listicle → Guide**: turn the points into sequential steps, add transitions + prerequisites + "mistakes to avoid".
- **To FAQ**: extract the information as Q&A, phrase the questions like Google searches, direct answer in bold + development, fill in the missing PAA.

## Inherited rules (do not redefine here)
- **Substance** (direct answer, FAQ, sources, E-E-A-T) → `edito-refresh` skill.
- **Form** (asset preservation, clean HTML, tables, metadata, colored callouts
  forbidden) → `format-wordpress` skill.
- **Overall structure and colors** → the site's skill. Do not hardcode colors
  here. The templates above describe the ORDER of the sections, not their style.
