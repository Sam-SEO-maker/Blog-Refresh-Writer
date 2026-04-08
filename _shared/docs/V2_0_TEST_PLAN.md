# Test Plan: Single-Sheet Architecture v2.0

**Document**: End-to-End Testing & Validation Guide
**Version**: 2.0
**Date**: February 2026
**Status**: Ready for Testing

---

## Overview

This document outlines the comprehensive testing strategy for the new v2.0 single-sheet architecture, designed to validate that all components work correctly before full production deployment.

### Key Testing Objectives

✅ Verify data migration from 4-sheet to single-sheet structure
✅ Validate all batch operation methods (audit-gsc, audit-serp, decision, refresh)
✅ Confirm correct error handling and status tracking
✅ Test asset preservation rules (RULE D'OR)
✅ Validate Google Sheets API integration
✅ Test error messages in column V for diagnostics

---

## Test Environment Setup

### Prerequisites

```bash
# 1. Create test Google Sheet (copy from production)
#    Copy existing spreadsheet and rename: "Super Refresh Writer - TEST"

# 2. Verify service account access
ls -la "C:/Users/samue/.credentials/google/google-service-account.json"

# 3. Verify Python environment
python --version  # Python 3.9+
pip list | grep google-api-python-client

# 4. Create test outputs directory
mkdir -p outputs/test-blog-1/audits
mkdir -p outputs/test-blog-1/decisions
mkdir -p outputs/test-blog-1/refreshes
```

### Test Data Preparation

For testing, use these minimal test URLs:

**Test Blog**: `test-blog-1`

| URL | Keyword | Purpose |
|-----|---------|---------|
| `https://test.example.com/article-1` | "test keyword 1" | GSC audit test |
| `https://test.example.com/article-2` | "test keyword 2" | SERP audit test |
| `https://test.example.com/article-3` | "test keyword 3" | Decision engine test |

---

## Phase 1: Pre-Migration Testing

### 1.1 Verify Current Architecture

```bash
# Check that legacy sheets exist and have data
python -c "
from scripts.sheets import SheetsClient
client = SheetsClient('YOUR_TEST_SHEET_ID')

# Count rows in legacy sheets
urls = client._read_sheet('URLs_Input')
audit = client._read_sheet('Audit_Results')
refresh = client._read_sheet('Refresh_Results')
decision = client._read_sheet('Decision_Log')

print(f'URLs_Input: {len(urls)} rows')
print(f'Audit_Results: {len(audit)} rows')
print(f'Refresh_Results: {len(refresh)} rows')
print(f'Decision_Log: {len(decision)} rows')
"
```

**Expected Output**:
- URLs_Input: ≥ 1 (header + test URLs)
- Audit_Results: ≥ 1 (header + optional data)
- Refresh_Results: ≥ 1 (header + optional data)
- Decision_Log: ≥ 1 (header + optional data)

### 1.2 Test RefreshAuditRow Model

```bash
# Verify model creation and serialization
python -c "
from _shared.core.models import RefreshAuditRow, PostType

# Create test instance
row = RefreshAuditRow(
    blog_id='test-blog-1',
    blogpost_url='https://test.example.com/article-1',
    main_keyword='test keyword',
    title='Test Article',
    post_type=PostType.STANDALONE,
    action_blogpost='NO ACTION',
    status='',
    audit_gsc='AUDITING',
    audit_serp='AUDITING',
    impressions_30d=100,
    clicks_30d=5,
    ctr_30d=5.0
)

# Test serialization
as_list = row.to_list()
print(f'to_list() length: {len(as_list)} (expected: 22)')
print(f'First 5 items: {as_list[:5]}')

# Test deserialization
row2 = RefreshAuditRow.from_list(as_list)
print(f'Round-trip successful: {row2.blog_id == row.blog_id}')
"
```

**Expected Output**:
```
to_list() length: 22 (expected: 22)
First 5 items: ['test-blog-1', 'https://test.example.com/article-1', 'test keyword', 'Test Article', 'STANDALONE']
Round-trip successful: True
```

---

## Phase 2: Migration Testing

### 2.1 Dry-Run Migration

```bash
# Run migration in dry-run mode (default, safe)
python scripts/sheets/migrate_to_single_sheet.py \
  --spreadsheet-id YOUR_TEST_SHEET_ID \
  --dry-run
```

**Expected Output**:
```
[INFO] [DRY RUN] Starting migration for spreadsheet: ...
[INFO] Step 1: Reading legacy sheets...
[INFO]   URLs_Input rows: X
[INFO]   Audit_Results rows: Y
[INFO] Step 2: Indexing data by URL...
[INFO] Step 3: Building Refreshs_Audit sheet...
[INFO] Step 4: Merging data...
[INFO]   Merged X rows (including header)
[INFO] Step 5: [DRY RUN] Would write to Refreshs_Audit
[INFO]   Sample row (first data row):
[INFO]     blog_id: test-blog-1
[INFO]     blogpost_url: https://...
```

**Validation**:
- ✅ No errors in dry-run mode
- ✅ Correct row counts
- ✅ Sample row shows expected structure

### 2.2 Live Migration

After validating dry-run, execute live migration:

```bash
# Run migration in LIVE mode (writes to sheet)
python scripts/sheets/migrate_to_single_sheet.py \
  --spreadsheet-id YOUR_TEST_SHEET_ID \
  --live
```

**Expected Output**:
```
[INFO] [LIVE] Starting migration...
[INFO] Step 5: Writing to Refreshs_Audit...
[INFO]   ✓ Successfully written to Refreshs_Audit
[INFO] MIGRATION SUMMARY
[INFO] Total rows migrated: X
```

**Manual Verification in Google Sheet**:
- ✅ "Refreshs_Audit" sheet exists
- ✅ Header row has 22 columns (A-V)
- ✅ All test URLs present in column B
- ✅ Column F (action_blogpost) populated with 4 values (NO ACTION, PARTIAL REFRESH, etc.)
- ✅ Column H (audit_gsc) shows DONE or NOT_STARTED
- ✅ Column I (audit_serp) shows DONE or NOT_STARTED

---

## Phase 3: SheetsClient v2.0 Method Testing

### 3.1 Test `read_pending_for_gsc_audit()`

```python
# Test reading rows where audit_gsc = AUDITING
from scripts.sheets import SheetsClient

client = SheetsClient('YOUR_TEST_SHEET_ID')

# Manually set at least one row's audit_gsc to "AUDITING" in sheet first

rows = client.read_pending_for_gsc_audit()
print(f"Found {len(rows)} rows for GSC audit")

for row in rows:
    print(f"  {row.blogpost_url} ({row.blog_id})")
    assert row.audit_gsc == "AUDITING"
```

**Expected Output**:
```
Found 1 rows for GSC audit
  https://test.example.com/article-1 (test-blog-1)
```

### 3.2 Test `read_pending_for_serp_audit()`

```python
# Test reading rows where audit_serp = AUDITING
rows = client.read_pending_for_serp_audit()
print(f"Found {len(rows)} rows for SERP audit")

for row in rows:
    assert row.audit_serp == "AUDITING"
    assert row.main_keyword  # Should have keyword
```

### 3.3 Test `read_pending_for_decision()`

```python
# Manually set audit_gsc=DONE, audit_serp=DONE for test row

rows = client.read_pending_for_decision()
print(f"Found {len(rows)} rows for decision")

for row in rows:
    assert row.audit_gsc == "DONE"
    assert row.audit_serp == "DONE"
    assert not row.action_blogpost  # Should be empty
```

### 3.4 Test `read_pending_for_refresh()`

```python
# Manually set action_blogpost to test value

rows = client.read_pending_for_refresh("PARTIAL REFRESH")
print(f"Found {len(rows)} rows for PARTIAL REFRESH")

for row in rows:
    assert row.action_blogpost == "PARTIAL REFRESH"
```

### 3.5 Test `update_audit_gsc()`

```python
# Test updating GSC metrics
success = client.update_audit_gsc(
    url='https://test.example.com/article-1',
    status='DONE',
    metrics={
        'impressions_30d': 500,
        'clicks_30d': 25,
        'ctr_30d': 5.0,
    }
)

print(f"Update audit_gsc: {'✓' if success else '✗'}")

# Verify in sheet
rows = client.read_pending_for_gsc_audit()  # Re-read
if rows:
    assert rows[0].impressions_30d == 500
    print("✓ Metrics updated correctly")
```

**Manual Verification**:
- Column H should now show "DONE"
- Column J should show 500
- Column K should show 25
- Column L should show 5.0

### 3.6 Test `update_audit_serp()`

```python
# Test updating SERP data
success = client.update_audit_serp(
    url='https://test.example.com/article-1',
    status='DONE',
    serp_data={
        'people_also_ask': 'Question 1?, Question 2?, Question 3?',
        'secondary_keywords': 'variant1, variant2, variant3',
    }
)

print(f"Update audit_serp: {'✓' if success else '✗'}")

# Verify
rows = client._read_sheet("Refreshs_Audit")
for row in rows[1:]:
    if row[1] == 'https://test.example.com/article-1':
        assert row[12] == 'Question 1?, Question 2?, Question 3?'
        print("✓ SERP data updated correctly")
```

### 3.7 Test `update_decision()`

```python
# Test updating decision results
success = client.update_decision(
    url='https://test.example.com/article-1',
    action_blogpost='PARTIAL REFRESH',
    content_metrics={
        'word_count_before': 1500,
        'images_count': 6,
        'internal_links_count': 12,
    },
    cannibalization={
        'flag': False,
        'urls': '',
    }
)

print(f"Update decision: {'✓' if success else '✗'}")

# Verify
rows = client._read_sheet("Refreshs_Audit")
for row in rows[1:]:
    if row[1] == 'https://test.example.com/article-1':
        assert row[5] == 'PARTIAL REFRESH'  # F
        assert row[16] == '1500'  # Q
        print("✓ Decision updated correctly")
```

### 3.8 Test `update_refresh_status()`

```python
# Test updating refresh status
success = client.update_refresh_status(
    url='https://test.example.com/article-1',
    status='TITLES DONE',
    new_titles={
        'new_h1_title': 'Updated H1 Title',
        'new_h2_titles': '["H2 1", "H2 2", "H2 3"]',
    }
)

print(f"Update refresh status: {'✓' if success else '✗'}")

# Verify
rows = client._read_sheet("Refreshs_Audit")
for row in rows[1:]:
    if row[1] == 'https://test.example.com/article-1':
        assert row[6] == 'TITLES DONE'  # G
        assert row[14] == 'Updated H1 Title'  # O
        print("✓ Refresh status updated correctly")
```

---

## Phase 4: Batch Operations Testing

### 4.1 Test `batch_audit_gsc()`

```bash
# Set up test row with audit_gsc = AUDITING in sheet

python main.py --mode batch-audit-gsc --blog-id test-blog-1
```

**Expected Output**:
```
🔍 Batch Audit GSC
✅ Traité: 1, Succès: 1, Échecs: 0
```

**Manual Verification**:
- Column H changed from AUDITING to DONE
- Columns J, K, L populated with metrics

### 4.2 Test `batch_audit_serp()`

```bash
# Set up test row with audit_serp = AUDITING in sheet

python main.py --mode batch-audit-serp --blog-id test-blog-1
```

**Expected Output**:
```
🔍 Batch Audit SERP
✅ Traité: 1, Succès: 1, Échecs: 0
```

**Manual Verification**:
- Column I changed to DONE
- Columns M, N populated with SERP data

### 4.3 Test `batch_decision()`

```bash
# Ensure both audits are DONE first, then run decision

python main.py --mode batch-decision --blog-id test-blog-1
```

**Expected Output**:
```
🎯 Batch Decision
✅ Actions: NO ACTION=0, PARTIAL=1, TITLES=0, FULL=0
```

**Manual Verification**:
- Column F populated with one of 4 values
- Columns Q-U filled with content metrics

### 4.4 Test `batch_refresh()`

```bash
# Test REFRESH TITLES
python main.py --mode batch-refresh --action REFRESH_TITLES --blog-id test-blog-1
```

**Expected Output**:
```
✍️ Batch Refresh (REFRESH_TITLES)
✅ Traité: 1, Succès: 1, Assets restaurés: 0
```

**Manual Verification**:
- Column G shows TITLES DONE
- Columns O, P updated

### 4.5 Test Error Handling

Test error cases to verify error_message column (V) works:

```bash
# Try batch operation with invalid blog_id
python main.py --mode batch-audit-gsc --blog-id nonexistent
```

**Expected Output**:
```
✅ Traité: 0, Succès: 0, Échecs: 0
```

---

## Phase 5: End-to-End Workflow Test

### Complete Test Scenario

**Manual Setup** (in Google Sheet):
1. Add test row to Refreshs_Audit with columns A-E filled:
   - blog_id: test-blog-1
   - blogpost_url: https://test.example.com/article
   - main_keyword: test keyword
   - title: Test Article
   - post_type: STANDALONE

2. Set H=AUDITING, I=AUDITING

**Execute Workflow**:

```bash
# Step 1: GSC Audit
python main.py --mode batch-audit-gsc --blog-id test-blog-1
# → H becomes DONE, J-L populated

# Step 2: SERP Audit
python main.py --mode batch-audit-serp --blog-id test-blog-1
# → I becomes DONE, M-N populated

# Step 3: Decision
python main.py --mode batch-decision --blog-id test-blog-1
# → F populated (NO ACTION, PARTIAL, TITLES, or FULL)
# → Q-U populated

# Step 4a: Refresh Titles (if REFRESH TITLES)
python main.py --mode batch-refresh --action REFRESH_TITLES --blog-id test-blog-1
# → G = TITLES DONE, O-P updated

# Step 4b: Refresh Content (if FULL REFRESH)
python main.py --mode batch-refresh --action FULL_REFRESH --blog-id test-blog-1
# → G = CONTENT DONE
```

**Final Verification** (in Google Sheet):
- ✅ Row complete: A-V all populated appropriately
- ✅ No empty cells in critical columns (H, I, F, G)
- ✅ Column V empty (no errors)
- ✅ Column T shows YES/NO (cannibalization flag)

---

## Phase 6: Error Scenarios Testing

### 6.1 Test Error Message Handling

```python
# Simulate audit failure
from scripts.sheets import SheetsClient

client = SheetsClient('YOUR_TEST_SHEET_ID')

# Update with error message
success = client.update_audit_gsc(
    url='https://test.example.com/article-1',
    status='FAILED',
    error_message='GSC quota exceeded'
)

# Verify column V
rows = client._read_sheet("Refreshs_Audit")
for row in rows[1:]:
    if row[1] == 'https://test.example.com/article-1':
        print(f"Column V (error): {row[21] if len(row) > 21 else 'EMPTY'}")
        assert row[21] == 'GSC quota exceeded'
```

### 6.2 Test Asset Preservation

When implementing `batch_refresh()` with actual content:

```python
# Verify assets are preserved
original_html = '<img src="image1.jpg"> <img src="image2.jpg">'
new_content = '<h2>New Content</h2>'

# AssetManager should ensure both images are present
validation = asset_manager.validate(
    original_assets=[...],
    new_content=new_content
)

print(f"Assets preserved: {validation.is_valid}")
assert validation.is_valid, "Assets not preserved!"
```

---

## Phase 7: Blog-ID Filtering Test

### Test filtering by blog_id

```bash
# Add another test URL for different blog
# blog_id: other-blog

# Filter by blog_id
python main.py --mode batch-audit-gsc --blog-id test-blog-1
# Should only process test-blog-1 URLs

python main.py --mode batch-audit-gsc --blog-id other-blog
# Should only process other-blog URLs
```

---

## Test Checklist

### Pre-Migration ✓
- [ ] Verify legacy sheets have data
- [ ] Test RefreshAuditRow model serialization
- [ ] Check Google API credentials work

### Migration ✓
- [ ] Run dry-run without errors
- [ ] Validate dry-run output structure
- [ ] Run live migration
- [ ] Verify Refreshs_Audit sheet created
- [ ] Validate column counts (22 columns)
- [ ] Check sample row data

### SheetsClient Methods ✓
- [ ] read_pending_for_gsc_audit() returns correct rows
- [ ] read_pending_for_serp_audit() returns correct rows
- [ ] read_pending_for_decision() returns correct rows
- [ ] read_pending_for_refresh() returns correct rows
- [ ] update_audit_gsc() updates H, J-L, V
- [ ] update_audit_serp() updates I, M-N, V
- [ ] update_decision() updates F, Q-U
- [ ] update_refresh_status() updates G, O-P

### Batch Operations ✓
- [ ] batch_audit_gsc() succeeds and updates sheet
- [ ] batch_audit_serp() succeeds and updates sheet
- [ ] batch_decision() succeeds and updates sheet
- [ ] batch_refresh() succeeds and updates sheet
- [ ] All operations respect --blog-id filter
- [ ] Error handling works (column V populated on FAILED)

### End-to-End ✓
- [ ] Complete workflow runs without errors
- [ ] Data flows correctly through all phases
- [ ] Final row has all columns populated
- [ ] Asset preservation rule enforced

### Error Scenarios ✓
- [ ] Error messages appear in column V
- [ ] Failed operations don't corrupt data
- [ ] Rollback/retry possible without duplication

---

## Success Criteria

✅ **All tests pass**: Every test case completes successfully
✅ **No data loss**: Migration preserves all original data
✅ **Correct structure**: Refreshs_Audit has 22 columns, correct headers
✅ **API integration**: Google Sheets read/write operations reliable
✅ **Batch operations**: All 4 batch modes work correctly
✅ **Error handling**: Errors trapped and logged without crashes
✅ **Asset preservation**: No images/links lost in refresh operations

---

## Rollback Plan

If critical issues found:

1. **Immediate**: Stop all batch operations
2. **Restore**: Copy data from legacy sheets back to URLs_Input
3. **Investigate**: Review error messages in column V
4. **Fix**: Update code and re-test
5. **Retry**: Run migration again with fixes

Rollback is safe because legacy sheets remain intact during migration.

---

## Next Steps After Testing

1. ✅ All tests pass → Proceed to production
2. ⚠️ Some tests fail → Fix code issues and retest
3. ❌ Major failures → Review architecture, consider alternate approach

Once production deployment:
- Monitor batch operations closely
- Archive legacy sheets after 30 days (retention policy)
- Update documentation
- Train team on new CLI batch modes

---

**Test Plan Owner**: Claude Agent
**Last Updated**: February 2026
**Version**: 2.0 - Final
