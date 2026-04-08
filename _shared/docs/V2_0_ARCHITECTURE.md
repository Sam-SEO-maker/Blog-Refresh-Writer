# v2.0 Single-Sheet Architecture

**System**: Super Refresh Writer v2.0
**Release Date**: February 2026
**Status**: Complete Implementation ✅

---

## Executive Summary

The v2.0 architecture consolidates the legacy 4-sheet Google Sheets structure into a **single unified sheet** with simplified batch operations.

### Key Changes

| Aspect | v1.0 (Legacy) | v2.0 (New) |
|--------|---------------|-----------|
| **Sheets** | 4 (URLs_Input, Audit_Results, Refresh_Results, Decision_Log) | 1 (Refreshs_Audit) + 2 archives |
| **Action Tracking** | 2 columns (to_do + recommended_actions) | 1 column (action_blogpost with 4 values) |
| **Status Tracking** | Scattered across sheets | Centralized in columns F-G |
| **Workflow** | Sequential auto-processing | Explicit batch CLI commands |
| **Error Diagnostics** | Log file inspection | Column V (error_message) |
| **Control** | Automatic | Manual batch operations |

---

## Architecture Overview

### Single-Sheet Structure: Refreshs_Audit (26 Columns A-V)

```
┌─────────────────────────────────────────────────────────────────┐
│         REFRESHS_AUDIT SHEET (26 Columns A-V)                  │
├─────────────────────────────────────────────────────────────────┤
│ A-E: Core Identification                                        │
│  A: blog_id                                                     │
│  B: blogpost_url                                                │
│  C: main_keyword                                                │
│  D: title                                                       │
│  E: post_type (PARENT/CHILD/STANDALONE)                        │
├─────────────────────────────────────────────────────────────────┤
│ F-G: Action & Status Tracking                                   │
│  F: action_blogpost (4 values: NO ACTION, PARTIAL REFRESH,     │
│                                 REFRESH TITLES, FULL REFRESH)   │
│  G: status (NO ACTION, TITLES DONE, CONTENT DONE)              │
├─────────────────────────────────────────────────────────────────┤
│ H-I: Audit Status Flags                                         │
│  H: audit_gsc (AUDITING, DONE, FAILED, NOT_STARTED)            │
│  I: audit_serp (AUDITING, DONE, FAILED, NOT_STARTED)           │
├─────────────────────────────────────────────────────────────────┤
│ J-L: GSC Performance Metrics                                    │
│  J: impressions_30d                                             │
│  K: clicks_30d                                                  │
│  L: ctr_30d                                                     │
├─────────────────────────────────────────────────────────────────┤
│ M-N: SERP Insights                                              │
│  M: people_also_ask (comma-separated PAA questions)             │
│  N: secondary_keywords (comma-separated variants)               │
├─────────────────────────────────────────────────────────────────┤
│ O-P: Refresh Optimization Targets                               │
│  O: new_h1_title                                                │
│  P: new_h2_titles (JSON list)                                   │
├─────────────────────────────────────────────────────────────────┤
│ Q-S: Content Metrics BEFORE Refresh                             │
│  Q: word_count_before                                           │
│  R: images_count                                                │
│  S: internal_links_count                                        │
├─────────────────────────────────────────────────────────────────┤
│ T-U: Cannibalization Tracking                                   │
│  T: cannibalization_flag (YES/NO)                               │
│  U: cannibalization_urls (comma-separated competing URLs)       │
├─────────────────────────────────────────────────────────────────┤
│ V: Error Diagnostics                                            │
│  V: error_message (short error for failed audit/refresh)        │
└─────────────────────────────────────────────────────────────────┘
```

### Action Column Values (Column F)

Four simplified values replace the complex to_do/recommended_actions system:

| Value | Meaning | Triggers | Output | User Action |
|-------|---------|----------|--------|-------------|
| **NO ACTION** | Article performs well, keep as-is | Good CTR, position, age < 6 months | None | Monitor only |
| **PARTIAL REFRESH** | Update stats/dates only | Age 12-18 months, good performance | Data updates | Review & approve |
| **REFRESH TITLES** | Optimize H1/H2 only | Low CTR with high impressions | New titles (O-P) | Review & approve |
| **FULL REFRESH** | Complete content rewrite | Multiple degraded signals | Full HTML | Review & publish |

### Status Column Values (Column G)

| Value | Meaning | When Set |
|-------|---------|----------|
| (empty) | Awaiting decision | After audit phase |
| **NO ACTION** | Decision made, no refresh needed | After batch_decision |
| **TITLES DONE** | H1/H2 optimized | After batch_refresh (REFRESH_TITLES) |
| **CONTENT DONE** | Full refresh complete | After batch_refresh (FULL_REFRESH) |

---

## Workflow: 4-Phase Batch Operations

### Phase 1: GSC Audit Batch

**Command**: `python main.py --mode batch-audit-gsc`

```
┌─────────────────────────────────┐
│ batch-audit-gsc                 │
├─────────────────────────────────┤
│ Process rows: H = AUDITING      │
│ For each row:                   │
│  1. Call audit_engine.analyze_gsc()  │
│  2. Extract metrics (J-L)       │
│  3. Update H → DONE/FAILED      │
│  4. Update V if error           │
└─────────────────────────────────┘

Columns Updated:
  H: audit_gsc (AUDITING → DONE/FAILED)
  J: impressions_30d
  K: clicks_30d
  L: ctr_30d
  V: error_message (if FAILED)
```

### Phase 2: SERP Audit Batch

**Command**: `python main.py --mode batch-audit-serp`

```
┌─────────────────────────────────┐
│ batch-audit-serp                │
├─────────────────────────────────┤
│ Process rows: I = AUDITING      │
│ For each row:                   │
│  1. Call audit_engine.analyze_serp() │
│  2. Extract SERP data (M-N)     │
│  3. Update I → DONE/FAILED      │
│  4. Update V if error           │
└─────────────────────────────────┘

Columns Updated:
  I: audit_serp (AUDITING → DONE/FAILED)
  M: people_also_ask
  N: secondary_keywords
  V: error_message (if FAILED)
```

### Phase 3: Decision Batch

**Command**: `python main.py --mode batch-decision`

```
┌─────────────────────────────────┐
│ batch-decision                  │
├─────────────────────────────────┤
│ Process rows: H=DONE AND I=DONE │
│         AND F empty             │
│ For each row:                   │
│  1. DecisionEngine.evaluate()   │
│  2. Map action → 4 values (F)   │
│  3. Extract content metrics     │
│  4. Check cannibalization       │
│  5. Update F, Q-U               │
└─────────────────────────────────┘

Columns Updated:
  F: action_blogpost (→ 4 values)
  Q: word_count_before
  R: images_count
  S: internal_links_count
  T: cannibalization_flag
  U: cannibalization_urls
```

### Phase 4: Refresh Batch

**Command**: `python main.py --mode batch-refresh --action PARTIAL_REFRESH|REFRESH_TITLES|FULL_REFRESH`

```
┌──────────────────────────────────────┐
│ batch-refresh                        │
├──────────────────────────────────────┤
│ Process rows: F = action value AND   │
│              G ≠ CONTENT DONE        │
│ For each row:                        │
│  1. Determine refresh type (O-P)     │
│  2. Generate new content             │
│  3. Validate assets (RULE D'OR)      │
│  4. Update G, O-P                    │
│  5. Save outputs/{blog_id}/refreshes │
└──────────────────────────────────────┘

Columns Updated:
  G: status (→ TITLES DONE or CONTENT DONE)
  O: new_h1_title
  P: new_h2_titles
```

---

## CLI Reference

### Command Syntax

```bash
python main.py --mode <batch-mode> [--action <action>] [--blog-id <blog-id>]
```

### Available Modes

#### 1. GSC Audit Batch

```bash
# Process all URLs with audit_gsc = AUDITING
python main.py --mode batch-audit-gsc

# Filter by blog
python main.py --mode batch-audit-gsc --blog-id enseigna

# Filter by blog and action
python main.py --mode batch-audit-gsc --blog-id moments-yoga
```

**Output Example**:
```
🔍 Batch Audit GSC
✅ Traité: 5, Succès: 4, Échecs: 1
```

#### 2. SERP Audit Batch

```bash
python main.py --mode batch-audit-serp [--blog-id <blog-id>]
```

**Output Example**:
```
🔍 Batch Audit SERP
✅ Traité: 5, Succès: 5, Échecs: 0
```

#### 3. Decision Batch

```bash
python main.py --mode batch-decision [--blog-id <blog-id>]
```

**Output Example**:
```
🎯 Batch Decision
✅ Actions: NO ACTION=2, PARTIAL=2, TITLES=1, FULL=0
```

#### 4. Refresh Batch

```bash
# PARTIAL REFRESH (stats/dates)
python main.py --mode batch-refresh --action PARTIAL_REFRESH [--blog-id <blog-id>]

# REFRESH TITLES (H1/H2 optimization)
python main.py --mode batch-refresh --action REFRESH_TITLES [--blog-id <blog-id>]

# FULL REFRESH (complete rewrite)
python main.py --mode batch-refresh --action FULL_REFRESH [--blog-id <blog-id>]
```

**Output Example**:
```
✍️ Batch Refresh (FULL_REFRESH)
✅ Traité: 3, Succès: 3, Assets restaurés: 0
```

---

## Complete Workflow Example

### Day 1: Initial Setup

**1. Migrate from legacy sheets** (one-time):

```bash
# Dry-run first (safe preview)
python scripts/sheets/migrate_to_single_sheet.py \
  --spreadsheet-id YOUR_SHEET_ID \
  --dry-run

# Review output, then go live
python scripts/sheets/migrate_to_single_sheet.py \
  --spreadsheet-id YOUR_SHEET_ID \
  --live
```

**2. Verify migration** in Google Sheet:
- ✅ "Refreshs_Audit" sheet created
- ✅ All URLs migrated (check row count)
- ✅ Column F populated with 4 values (or empty if new)
- ✅ Columns H-I set appropriately

### Day 2-N: Batch Processing Workflow

**Setup in Google Sheet** (manual):
1. Add URL to Refreshs_Audit (columns A-E)
2. Set H = AUDITING, I = AUDITING

**Automated Process**:

```bash
# Step 1: GSC Audit (~ 1-2 minutes per URL)
python main.py --mode batch-audit-gsc --blog-id enseigna

# ✅ Verify in sheet:
#    Column H = DONE, J-L = metrics

# Step 2: SERP Audit (~ 1-2 minutes per URL)
python main.py --mode batch-audit-serp --blog-id enseigna

# ✅ Verify in sheet:
#    Column I = DONE, M-N = SERP data

# Step 3: Decision Engine (~ 5 seconds per URL)
python main.py --mode batch-decision --blog-id enseigna

# ✅ Verify in sheet:
#    Column F = action value, Q-U = content metrics

# Step 4: Refresh (varies by action)
# Option A: Refresh titles only
python main.py --mode batch-refresh --action REFRESH_TITLES --blog-id enseigna
# ✅ Column G = TITLES DONE, O-P = new titles

# Option B: Full refresh
python main.py --mode batch-refresh --action FULL_REFRESH --blog-id enseigna
# ✅ Column G = CONTENT DONE
# ✅ outputs/{blog_id}/refreshes/ populated
```

**Manual Review & Publish** (user):
1. Review new H1/H2 titles (columns O-P)
2. Review new HTML (if FULL REFRESH)
3. Delete row from Refreshs_Audit (workflow complete)
4. Publish to WordPress (manual or via API)

---

## Migration Guide

### From v1.0 to v2.0

**Step 1: Backup Current System**

```bash
# Export all sheets as CSV
# - URLs_Input.csv
# - Audit_Results.csv
# - Refresh_Results.csv
# - Decision_Log.csv
```

**Step 2: Run Migration Script**

```bash
# Create test copy of spreadsheet first
# Then run migration on test copy

python scripts/sheets/migrate_to_single_sheet.py \
  --spreadsheet-id TEST_SHEET_ID \
  --dry-run

# Validate dry-run output, then go live
python scripts/sheets/migrate_to_single_sheet.py \
  --spreadsheet-id TEST_SHEET_ID \
  --live
```

**Step 3: Validate Migration**

Use **[V2_0_TEST_PLAN.md](V2_0_TEST_PLAN.md)** for complete testing checklist.

**Step 4: Production Deployment**

```bash
# After validation on test sheet:
python scripts/sheets/migrate_to_single_sheet.py \
  --spreadsheet-id PRODUCTION_SHEET_ID \
  --live
```

**Step 5: Archive Legacy Sheets** (optional)

After 30-day retention:
- Rename "Audit_Results" → "Audit_Results_ARCHIVED_2026-03-15"
- Delete or archive Audit_Results (keep Decision_Log, Refresh_Results for history)

---

## Error Handling

### Column V: Error Messages

Errors are captured in column V with short, descriptive messages:

**GSC Audit Errors**:
- "GSC quota exceeded" → Exceeded API quota limit
- "URL not indexed" → URL not found in Google Search Console
- "No GSC property" → Property not configured

**SERP Audit Errors**:
- "DataForSEO quota" → API quota exceeded
- "Keyword not found" → No SERP results for keyword
- "API timeout" → DataForSEO service timeout

**Decision Engine Errors**:
- "Missing metrics" → Incomplete audit data
- "Ambiguous action" → Unable to determine strategy

**Refresh Errors**:
- "Asset validation" → Images/links not preserved
- "LLM quota" → Claude API quota exceeded
- "Invalid HTML" → Generated content syntax error

### Recovery Workflow

1. **Identify Error**: Check column V
2. **Fix Root Cause**:
   - GSC API limit? Wait 1 hour, retry
   - Missing keyword? Add to column C, re-run SERP audit
   - Asset validation? Check output in V2_0_TEST_PLAN.md
3. **Retry Operation**: Clear column V, re-run batch command
4. **Escalate if Needed**: Review logs for detailed error

---

## Key Improvements Over v1.0

### 1. Simplified Status Tracking

**Before (v1.0)**: Complex 2-column system
```
to_do | recommended_actions
"Réécriture partielle" | "✓ 3 dates mise à jour (→2026) | → Stratégie: PARTIAL_REFRESH | ⚠️ CTR faible malgré visibilité"
```

**After (v2.0)**: Single 4-value column
```
action_blogpost
"PARTIAL REFRESH"
```

### 2. Explicit Control Flow

**Before**: Auto-triggered at unknown times
**After**: Manual batch commands with visibility

```bash
python main.py --mode batch-audit-gsc  # Clear, explicit, loggable
```

### 3. In-Sheet Diagnostics

**Before**: Must read Python logs
**After**: Errors visible in column V

```
Column V: "GSC quota exceeded"  # Immediate visibility
```

### 4. Batch Processing

**Before**: One URL at a time, sequential
**After**: Multiple URLs in one command

```bash
python main.py --mode batch-decision --blog-id enseigna
# Processes all pending URLs for enseigna in one call
```

### 5. Multi-Tenant Support

**Before**: No blog filtering
**After**: Process specific blog only

```bash
python main.py --mode batch-audit-gsc --blog-id moments-yoga
# Only processes moments-yoga URLs
```

---

## Technical Details

### RefreshAuditRow Model

Located in `_shared/core/models/sheets_models.py`:

```python
@dataclass
class RefreshAuditRow:
    # 22 fields, serializable to/from Google Sheets
    blog_id: str
    blogpost_url: str
    # ... (20 more fields)

    def to_list(self) -> list:
        """Convert to 22-element list for Google Sheets"""

    @staticmethod
    def from_list(row: list, row_index: int = 0) -> "RefreshAuditRow":
        """Parse from 22-element Google Sheets row"""
```

### SheetsClient v2.0 Methods

Located in `scripts/sheets/sheets_client.py`:

```python
# Reading methods
read_pending_for_gsc_audit(blog_id: Optional[str])
read_pending_for_serp_audit(blog_id: Optional[str])
read_pending_for_decision(blog_id: Optional[str])
read_pending_for_refresh(action: str, blog_id: Optional[str])

# Writing methods
update_audit_gsc(url, status, metrics, error_message)
update_audit_serp(url, status, serp_data, error_message)
update_decision(url, action_blogpost, content_metrics, cannibalization)
update_refresh_status(url, status, new_titles)
```

### Orchestrator Batch Methods

Located in `scripts/agent/orchestrator.py`:

```python
def batch_audit_gsc(blog_id: Optional[str]) -> dict
def batch_audit_serp(blog_id: Optional[str]) -> dict
def batch_decision(blog_id: Optional[str]) -> dict
def batch_refresh(action: str, blog_id: Optional[str]) -> dict
```

---

## Files Modified

### Core Implementation (Committed)
- ✅ `_shared/core/models/sheets_models.py` - RefreshAuditRow model
- ✅ `scripts/sheets/sheets_client.py` - v2.0 methods
- ✅ `scripts/utils/action_formatter.py` - map_action_to_blogpost()
- ✅ `scripts/agent/orchestrator.py` - batch operations
- ✅ `main.py` - CLI batch modes

### New Files (Committed)
- ✅ `scripts/sheets/migrate_to_single_sheet.py` - Migration script
- ✅ `_shared/docs/V2_0_ARCHITECTURE.md` - This file
- ✅ `_shared/docs/V2_0_TEST_PLAN.md` - Testing guide

### Legacy Files (Preserved)
- URLTask, AuditResultRow, RefreshResultRow (deprecated, kept for backwards compat)
- Legacy sheet names preserved for archive operations

---

## Appendix: Column Reference

| Col | Name | Type | Values | Updated By |
|-----|------|------|--------|------------|
| A | blog_id | String | Site ID | User (manual) |
| B | blogpost_url | String | Full URL | User (manual) |
| C | main_keyword | String | Target keyword | User (manual) |
| D | title | String | Article title | User (manual) |
| E | post_type | Enum | PARENT/CHILD/STANDALONE | User (manual) |
| F | action_blogpost | Enum | 4 values | batch_decision |
| G | status | String | NO ACTION / TITLES DONE / CONTENT DONE | batch_refresh |
| H | audit_gsc | String | AUDITING/DONE/FAILED | batch_audit_gsc |
| I | audit_serp | String | AUDITING/DONE/FAILED | batch_audit_serp |
| J | impressions_30d | Integer | GSC metric | batch_audit_gsc |
| K | clicks_30d | Integer | GSC metric | batch_audit_gsc |
| L | ctr_30d | Float | GSC metric % | batch_audit_gsc |
| M | people_also_ask | String | Comma-sep questions | batch_audit_serp |
| N | secondary_keywords | String | Comma-sep keywords | batch_audit_serp |
| O | new_h1_title | String | Optimized H1 | batch_refresh |
| P | new_h2_titles | String | JSON list | batch_refresh |
| Q | word_count_before | Integer | Original word count | batch_decision |
| R | images_count | Integer | Original image count | batch_decision |
| S | internal_links_count | Integer | Original link count | batch_decision |
| T | cannibalization_flag | Boolean | YES/NO | batch_decision |
| U | cannibalization_urls | String | Comma-sep URLs | batch_decision |
| V | error_message | String | Error description | Any batch op |

---

## Getting Help

### Quick Issues

| Problem | Solution |
|---------|----------|
| Import error | `pip install google-api-python-client google-auth-oauthlib` |
| API auth fail | Check service account path: `C:/Users/samue/.credentials/google/...` |
| Column mismatch | Run dry-run migration first: `--dry-run` (default) |
| No rows found | Verify `audit_gsc=AUDITING` before running `batch-audit-gsc` |

### Detailed Support

- **Testing**: See [V2_0_TEST_PLAN.md](V2_0_TEST_PLAN.md)
- **Error Messages**: Check column V in Google Sheet
- **Code Issues**: Review logs in `debug_output.txt`
- **Architecture Q&A**: This file (V2_0_ARCHITECTURE.md)

---

**v2.0 Architecture Complete** ✅
**Ready for Testing & Production Deployment**

*Last Updated: February 11, 2026*
*Status: Fully Implemented*
