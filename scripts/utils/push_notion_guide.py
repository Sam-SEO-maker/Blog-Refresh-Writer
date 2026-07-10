#!/usr/bin/env python3
"""Push ONBOARDING_HAILEY_US.md to a Notion page via REST API."""
import json, re, os, sys, requests
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────────
TOKEN = os.environ.get("NOTION_TOKEN", "")
PARENT_ID = "37ad6418-695a-80f1-a207-cbff3237a908"
MD_FILE = Path(__file__).parent.parent.parent / "_shared/docs/ONBOARDING_HAILEY_US.md"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# ── Inline markdown → Notion rich_text ──────────────────────────────────────
def parse_inline(text: str) -> list:
    result = []
    i = 0
    buf = ""

    def flush(bold=False, italic=False, code=False, url=None):
        nonlocal buf
        if buf:
            obj = {"type": "text", "text": {"content": buf}}
            ann = {}
            if bold:   ann["bold"]   = True
            if italic: ann["italic"] = True
            if code:   ann["code"]   = True
            if ann:    obj["annotations"] = ann
            if url:    obj["text"]["link"] = {"url": url}
            result.append(obj)
            buf = ""

    while i < len(text):
        # Bold **
        if text[i:i+2] == "**":
            flush()
            end = text.find("**", i + 2)
            if end == -1:
                buf += text[i]; i += 1; continue
            inner = text[i+2:end]
            flush(bold=True) if False else result.append(
                {"type": "text", "text": {"content": inner}, "annotations": {"bold": True}}
            )
            i = end + 2; continue
        # Inline code `
        if text[i] == "`":
            flush()
            end = text.find("`", i + 1)
            if end == -1:
                buf += text[i]; i += 1; continue
            result.append({"type": "text", "text": {"content": text[i+1:end]},
                           "annotations": {"code": True}})
            i = end + 1; continue
        # Link [text](url) — skip anchor-only links (#...)
        if text[i] == "[":
            m = re.match(r'\[([^\]]+)\]\(([^\)]+)\)', text[i:])
            if m:
                flush()
                url = m.group(2)
                if url.startswith("#") or not url.startswith("http"):
                    # Render as plain bold text, no link
                    result.append({"type": "text", "text": {"content": m.group(1)}})
                else:
                    result.append({"type": "text",
                                   "text": {"content": m.group(1), "link": {"url": url}}})
                i += m.end(); continue
        # Italic *
        if text[i] == "*" and text[i:i+2] != "**":
            flush()
            end = text.find("*", i + 1)
            if end == -1:
                buf += text[i]; i += 1; continue
            result.append({"type": "text", "text": {"content": text[i+1:end]},
                           "annotations": {"italic": True}})
            i = end + 1; continue
        buf += text[i]; i += 1

    flush()
    return result or [{"type": "text", "text": {"content": ""}}]

# ── Block helpers ────────────────────────────────────────────────────────────
def blk(type_, rt=None, **kw):
    b = {"object": "block", "type": type_, type_: {}}
    if rt is not None:
        b[type_]["rich_text"] = rt
    b[type_].update(kw)
    return b

CALLOUT_MAP = {
    "🚨": ("🚨", "red_background"),
    "⚠️": ("⚠️", "orange_background"),
    "ℹ️": ("ℹ️", "blue_background"),
    "💡": ("💡", "yellow_background"),
}

def make_callout(text: str):
    icon, color = "💡", "yellow_background"
    stripped = text.strip()
    for emoji, (ic, col) in CALLOUT_MAP.items():
        if stripped.startswith(emoji):
            icon, color = ic, col
            stripped = stripped[len(emoji):].lstrip()
            break
    # Also detect by keyword
    low = stripped.lower()
    if any(low.startswith(k) for k in ("**warning", "⚠", "always activate", "copy the password",
                                        "never share", "always paste", "ask before")):
        icon, color = "⚠️", "orange_background"
    elif any(low.startswith(k) for k in ("🚨", "**important", "your .env")):
        icon, color = "🚨", "red_background"
    elif any(low.startswith(k) for k in ("ℹ️", "**note", "your daily", "google sheets is")):
        icon, color = "ℹ️", "blue_background"
    return {
        "object": "block", "type": "callout",
        "callout": {
            "rich_text": parse_inline(stripped),
            "icon": {"type": "emoji", "emoji": icon},
            "color": color,
        }
    }

def parse_table(table_lines: list):
    rows = []
    for line in table_lines:
        if re.match(r'^\s*\|[-:| ]+\|\s*$', line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells:
            rows.append(cells)
    if not rows:
        return None
    width = max(len(r) for r in rows)
    row_blocks = []
    for row in rows:
        padded = row + [""] * (width - len(row))
        cells = [[{"type": "text", "text": {"content": c}}] for c in padded]
        row_blocks.append({
            "object": "block", "type": "table_row",
            "table_row": {"cells": cells}
        })
    return {
        "object": "block", "type": "table",
        "table": {
            "table_width": width,
            "has_column_header": True,
            "has_row_header": False,
            "children": row_blocks,
        },
    }

# ── Markdown → blocks ────────────────────────────────────────────────────────
def md_to_blocks(text: str) -> list:
    lines = text.split("\n")
    blocks = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Code block
        if line.startswith("```"):
            lang = line[3:].strip() or "plain text"
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            blocks.append(blk("code",
                rt=[{"type": "text", "text": {"content": "\n".join(code_lines)}}],
                language=lang))
            i += 1; continue

        # Table
        if line.startswith("|"):
            tbl_lines = []
            while i < len(lines) and lines[i].startswith("|"):
                tbl_lines.append(lines[i]); i += 1
            t = parse_table(tbl_lines)
            if t: blocks.append(t)
            continue

        # Divider (must come before heading check since --- is also setext heading)
        if re.match(r'^-{3,}\s*$', line):
            blocks.append({"object": "block", "type": "divider", "divider": {}})
            i += 1; continue

        # Headings
        if line.startswith("#### "): blocks.append(blk("heading_3", rt=parse_inline(line[5:])))
        elif line.startswith("### "): blocks.append(blk("heading_3", rt=parse_inline(line[4:])))
        elif line.startswith("## "):  blocks.append(blk("heading_2", rt=parse_inline(line[3:])))
        elif line.startswith("# "):   blocks.append(blk("heading_1", rt=parse_inline(line[2:])))

        # Callout (blockquote)
        elif line.startswith("> "):
            content_parts = [line[2:]]
            while i + 1 < len(lines) and lines[i+1].startswith("> "):
                i += 1
                content_parts.append(lines[i][2:])
            blocks.append(make_callout(" ".join(content_parts)))

        # To-do
        elif line.startswith("- [ ] "):
            blocks.append(blk("to_do", rt=parse_inline(line[6:]), checked=False))
        elif line.startswith("- [x] "):
            blocks.append(blk("to_do", rt=parse_inline(line[6:]), checked=True))

        # Lists
        elif re.match(r'^[-*] ', line):
            blocks.append(blk("bulleted_list_item", rt=parse_inline(line[2:])))
        elif re.match(r'^\d+\. ', line):
            blocks.append(blk("numbered_list_item", rt=parse_inline(re.sub(r'^\d+\. ', '', line))))

        # Paragraph
        elif line.strip():
            blocks.append(blk("paragraph", rt=parse_inline(line)))

        i += 1

    return blocks

# ── Two-pass creator: handles tables that need child rows appended ───────────
def create_page_and_push(title: str, blocks: list) -> str:
    """Create page, return page_id. Handles table child rows via separate calls."""

    def strip_private(b):
        """Remove internal helper keys not accepted by Notion API."""
        b = dict(b)
        b.pop("_rows", None)
        return b

    # Build page-creation payload (no table children inline)
    clean_blocks = [strip_private(b) for b in blocks[:100]]

    resp = requests.post(
        "https://api.notion.com/v1/pages",
        headers=HEADERS,
        json={
            "parent": {"type": "page_id", "page_id": PARENT_ID},
            "properties": {
                "title": {"title": [{"type": "text", "text": {"content": title}}]}
            },
            "children": clean_blocks,
        },
    )
    if resp.status_code not in (200, 201):
        print(f"ERROR creating page: {resp.status_code}")
        print(resp.text[:800])
        sys.exit(1)

    page_id = resp.json()["id"]
    print(f"✓ Page created: {page_id}")

    # Append remaining blocks in batches of 100
    remaining = blocks[100:]
    batch_num = 1
    while remaining:
        batch_raw, remaining = remaining[:100], remaining[100:]
        clean = [strip_private(b) for b in batch_raw]
        r = requests.patch(
            f"https://api.notion.com/v1/blocks/{page_id}/children",
            headers=HEADERS,
            json={"children": clean},
        )
        if r.status_code not in (200, 201):
            print(f"  WARN batch {batch_num}: {r.status_code} {r.text[:200]}")
        else:
            print(f"  ✓ batch {batch_num} ({len(clean)} blocks)")
        batch_num += 1


    return page_id


def _get_block_id_for_table(page_id: str, table_block: dict) -> str | None:
    """Find the block ID of a table block inside a page."""
    r = requests.get(
        f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=100",
        headers=HEADERS,
    )
    if r.status_code != 200:
        return None
    for blk_ in r.json().get("results", []):
        if blk_.get("type") == "table":
            width = blk_.get("table", {}).get("table_width", 0)
            expected = table_block["table"]["table_width"]
            if width == expected:
                return blk_["id"]
    return None


def _append_table(page_id: str, table_block: dict):
    """Create a table block then append its rows."""
    rows = table_block.get("_rows", [])
    clean_table = {k: v for k, v in table_block.items() if k not in ("_rows", "children", "object")}
    clean_table = {"object": "block", "type": "table", "table": table_block["table"]}

    # Append table block
    r = requests.patch(
        f"https://api.notion.com/v1/blocks/{page_id}/children",
        headers=HEADERS,
        json={"children": [clean_table]},
    )
    if r.status_code not in (200, 201):
        print(f"  WARN table create: {r.status_code} {r.text[:200]}")
        return

    table_id = r.json()["results"][0]["id"]
    _append_rows(table_id, rows)


def _append_table_rows_by_scanning(page_id: str, table_block: dict):
    rows = table_block.get("_rows", [])
    if not rows:
        return
    table_id = _get_block_id_for_table(page_id, table_block)
    if table_id:
        _append_rows(table_id, rows)


def _append_rows(table_id: str, rows: list):
    if not rows:
        return
    r = requests.patch(
        f"https://api.notion.com/v1/blocks/{table_id}/children",
        headers=HEADERS,
        json={"children": rows},
    )
    if r.status_code not in (200, 201):
        print(f"  WARN rows append to {table_id}: {r.status_code} {r.text[:200]}")
    else:
        print(f"  ✓ {len(rows)} rows → table {table_id[:8]}…")


# ── Main ─────────────────────────────────────────────────────────────────────
def clear_page_blocks(page_id: str):
    """Delete all existing blocks from a page."""
    all_ids = []
    cursor = None
    while True:
        url = f"https://api.notion.com/v1/blocks/{page_id}/children?page_size=100"
        if cursor:
            url += f"&start_cursor={cursor}"
        r = requests.get(url, headers=HEADERS).json()
        all_ids.extend(b["id"] for b in r.get("results", []))
        if not r.get("has_more"):
            break
        cursor = r.get("next_cursor")

    print(f"  Deleting {len(all_ids)} existing blocks…")
    for bid in all_ids:
        requests.delete(f"https://api.notion.com/v1/blocks/{bid}", headers=HEADERS)
    print(f"  ✓ Cleared")


def update_page(page_id: str, title: str, blocks: list):
    """Clear a page's content and replace with new blocks."""
    clear_page_blocks(page_id)

    # Update title
    requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=HEADERS,
        json={"properties": {"title": {"title": [{"type": "text", "text": {"content": title}}]}}},
    )

    # Append all blocks in batches of 100
    batch_num = 0
    remaining = list(blocks)
    while remaining:
        batch_raw, remaining = remaining[:100], remaining[100:]
        clean = [strip_private(b) for b in batch_raw]
        r = requests.patch(
            f"https://api.notion.com/v1/blocks/{page_id}/children",
            headers=HEADERS,
            json={"children": clean},
        )
        batch_num += 1
        if r.status_code not in (200, 201):
            print(f"  WARN batch {batch_num}: {r.status_code} {r.text[:200]}")
        else:
            print(f"  ✓ batch {batch_num} ({len(clean)} blocks)")

    return page_id


def strip_private(b):
    b = dict(b)
    b.pop("_rows", None)
    return b


def main():
    if not TOKEN:
        print("ERROR: NOTION_TOKEN not set"); sys.exit(1)

    # Existing page to update in place (pass as argument or set here)
    update_page_id = sys.argv[1] if len(sys.argv) > 1 else None

    text = MD_FILE.read_text(encoding="utf-8")

    m = re.match(r'^# (.+)', text, re.MULTILINE)
    title = m.group(1) if m else "Content Writer — Onboarding Guide"
    text = re.sub(r'^# .+\n', '', text, count=1)

    print(f"Parsing {MD_FILE.name} …")
    blocks = md_to_blocks(text)
    print(f"  {len(blocks)} blocks parsed")

    if update_page_id:
        print(f"Updating page {update_page_id} in place…")
        page_id = update_page(update_page_id, title, blocks)
    else:
        page_id = create_page_and_push(title, blocks)

    url = f"https://app.notion.com/p/{page_id.replace('-', '')}"
    print(f"\n✅ Done! {url}")


if __name__ == "__main__":
    main()
