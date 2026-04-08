# v2.0 Quick Reference Card

**Print this page or bookmark for easy command reference**

---

## Batch Operations Cheat Sheet

### GSC Audit (Google Search Console)

```bash
# All URLs needing GSC audit
python main.py --mode batch-audit-gsc

# Specific blog only
python main.py --mode batch-audit-gsc --blog-id enseigna

# Specific blog: moments-yoga
python main.py --mode batch-audit-gsc --blog-id moments-yoga
```

**Updates**: H (DONE/FAILED) | J-L (metrics) | V (error)

---

### SERP Audit (DataForSEO)

```bash
# All URLs needing SERP audit
python main.py --mode batch-audit-serp

# Specific blog only
python main.py --mode batch-audit-serp --blog-id courses-particuliers
```

**Updates**: I (DONE/FAILED) | M-N (SERP data) | V (error)

---

### Decision Engine

```bash
# All URLs ready for decision
python main.py --mode batch-decision

# Specific blog only
python main.py --mode batch-decision --blog-id mymusicteacher
```

**Updates**: F (action value) | Q-U (metrics + cannib.)

---

### Refresh (4 Variants)

```bash
# Partial Refresh: update stats/dates
python main.py --mode batch-refresh --action PARTIAL_REFRESH

# Refresh Titles: optimize H1/H2 only
python main.py --mode batch-refresh --action REFRESH_TITLES

# Full Refresh: complete rewrite
python main.py --mode batch-refresh --action FULL_REFRESH

# Specific blog + action
python main.py --mode batch-refresh --action FULL_REFRESH --blog-id coachsportlyon
```

**Updates**: G (status) | O-P (new titles)

---

## Column Reference (A-V)

| Col | Name | Example | Who Sets |
|-----|------|---------|----------|
| **A** | blog_id | `enseigna` | User |
| **B** | blogpost_url | `https://...` | User |
| **C** | main_keyword | `"cours particuliers"` | User |
| **D** | title | `"Article Title"` | User |
| **E** | post_type | `STANDALONE` | User |
| **F** | action_blogpost | `PARTIAL REFRESH` | Decision |
| **G** | status | `TITLES DONE` | Refresh |
| **H** | audit_gsc | `DONE` | GSC batch |
| **I** | audit_serp | `DONE` | SERP batch |
| **J** | impressions_30d | `500` | GSC batch |
| **K** | clicks_30d | `25` | GSC batch |
| **L** | ctr_30d | `5.0` | GSC batch |
| **M** | people_also_ask | `"Q1? Q2? Q3?"` | SERP batch |
| **N** | secondary_keywords | `"kw1, kw2, kw3"` | SERP batch |
| **O** | new_h1_title | `"New Title"` | Refresh |
| **P** | new_h2_titles | `"[...]"` | Refresh |
| **Q** | word_count_before | `1500` | Decision |
| **R** | images_count | `6` | Decision |
| **S** | internal_links_count | `12` | Decision |
| **T** | cannibalization_flag | `YES` or `NO` | Decision |
| **U** | cannibalization_urls | `"url1, url2"` | Decision |
| **V** | error_message | `"API quota exceeded"` | Any batch |

---

## Workflow States

### Audit Status (H, I)

| State | Meaning | Action |
|-------|---------|--------|
| **AUDITING** | Waiting to be processed | Run batch audit |
| **DONE** | Successfully completed | Check metrics |
| **FAILED** | Error occurred | Check column V |
| **NOT_STARTED** | No audit data yet | Not applicable |

### Action Values (F)

| Value | Word Count | Use Case |
|-------|-----------|----------|
| **NO ACTION** | 1 | Article performs well |
| **PARTIAL REFRESH** | 2 | Update stats only |
| **REFRESH TITLES** | 2 | Optimize H1/H2 |
| **FULL REFRESH** | 2 | Complete rewrite |

### Refresh Status (G)

| Value | Meaning | Next Step |
|-------|---------|-----------|
| (empty) | Not yet refreshed | Run batch_refresh |
| **TITLES DONE** | Titles optimized | Review O-P, publish |
| **CONTENT DONE** | Full refresh complete | Review HTML, publish |

---

## 6 Blogs in System

| blog_id | Domain | Tone |
|---------|--------|------|
| **enseigna** | enseigna.fr | Expert |
| **cours-particuliers** | cours-particuliers.com | Warm |
| **educationetdevenir** | educationetdevenir.fr | Informative |
| **moments-yoga** | moments-yoga.fr | Calming |
| **mymusicteacher** | mymusicteacher.fr | Enthusiastic |
| **coachsportlyon** | coachsportlyon.fr | Dynamic |

---

## Common Tasks

### Add New URL

1. Open "Refreshs_Audit" sheet
2. Add row with columns A-E filled:
   - A: blog_id
   - B: full URL
   - C: main keyword
   - D: article title
   - E: STANDALONE or PARENT or CHILD
3. Set H = AUDITING, I = AUDITING

### Run Complete Workflow

```bash
# 1. GSC Audit
python main.py --mode batch-audit-gsc --blog-id enseigna

# 2. SERP Audit
python main.py --mode batch-audit-serp --blog-id enseigna

# 3. Decision
python main.py --mode batch-decision --blog-id enseigna

# 4. Choose action and refresh
python main.py --mode batch-refresh --action PARTIAL_REFRESH --blog-id enseigna

# 5. Review and publish (manual)
```

### Check Status of URL

1. Open "Refreshs_Audit" sheet
2. Find URL in column B
3. Check columns:
   - H: Is GSC audit done?
   - I: Is SERP audit done?
   - F: What action is planned?
   - G: Has refresh been done?
   - V: Any errors?

### Debug Error

1. Check column V for error message
2. Common errors:
   - "GSC quota exceeded" → Wait 1 hour, retry
   - "URL not indexed" → Check Google Search Console
   - "Keyword not found" → Verify column C has keyword
3. Clear V and retry batch command

### Migrate from v1.0

```bash
# Dry-run (safe preview)
python scripts/sheets/migrate_to_single_sheet.py \
  --spreadsheet-id YOUR_ID \
  --dry-run

# Live migration
python scripts/sheets/migrate_to_single_sheet.py \
  --spreadsheet-id YOUR_ID \
  --live
```

---

## Error Messages (Column V)

### Audit Errors

```
GSC quota exceeded       → Wait 1 hour, retry
URL not indexed         → Not in Google Search Console
DataForSEO quota        → API quota exceeded
Keyword not found       → No results for keyword
API timeout             → Service unavailable, retry
```

### Decision Errors

```
Missing metrics         → Incomplete audit data
Ambiguous action        → Unable to determine strategy
```

### Refresh Errors

```
Asset validation failed → Images/links not preserved
LLM quota exceeded      → Claude API limit reached
Invalid HTML            → Syntax error in generated content
```

---

## File Locations

```
Project Root: c:\Users\samue\OneDrive\Bureau\Claude Code\Super Refresh Writer\

Config:
  _shared/config/decision_rules.json
  _shared/config/sites.json

Docs:
  _shared/docs/V2_0_ARCHITECTURE.md      ← Full reference
  _shared/docs/V2_0_TEST_PLAN.md         ← Testing guide
  _shared/docs/V2_0_QUICK_REFERENCE.md   ← This file

Scripts:
  main.py                                ← Entry point
  scripts/sheets/migrate_to_single_sheet.py
  scripts/agent/orchestrator.py
  scripts/sheets/sheets_client.py

Models:
  _shared/core/models/sheets_models.py
  _shared/core/models/workflow_models.py
```

---

## Keyboard Shortcuts (if using IDE)

```
Ctrl+Shift+P        → Command palette
Ctrl+F              → Find in file
Ctrl+H              → Find & replace
Alt+↑/↓             → Move line up/down
Ctrl+/              → Comment/uncomment
F5                  → Run/debug
```

---

## Key Principles

✅ **RULE D'OR**: Assets (images, links) always preserved or increased
✅ **Single Source of Truth**: Refreshs_Audit sheet is master
✅ **Manual Control**: User decides when to run batch ops
✅ **In-Sheet Diagnostics**: Errors visible in column V
✅ **Multi-Blog Support**: Filter by --blog-id

---

## Need Help?

| Question | Answer Location |
|----------|-----------------|
| What is v2.0 architecture? | V2_0_ARCHITECTURE.md |
| How do I test it? | V2_0_TEST_PLAN.md |
| What commands exist? | V2_0_QUICK_REFERENCE.md (this) |
| How do I migrate? | V2_0_ARCHITECTURE.md → Migration Guide |
| What's my error? | Check column V in sheet |
| Where's the code? | See File Locations above |

---

**v2.0 Single-Sheet Architecture**
**Quick Reference Guide**
*Print & Keep Handy*

Last Updated: February 2026
