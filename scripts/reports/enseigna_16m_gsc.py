"""Export GSC perf enseigna.fr - 16 mois - articles only (exclude /v/)."""
import csv
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

load_dotenv()

SA_PATH = Path(os.environ["GOOGLE_SA_PATH"]).expanduser()
SITE = "https://enseigna.fr/"

creds = service_account.Credentials.from_service_account_file(
    str(SA_PATH),
    scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
)
svc = build("searchconsole", "v1", credentials=creds)

end = datetime.now().date()
start = end - timedelta(days=487)  # ~16 mois

# Exclude WordPress system paths; keep only root-slug articles like /avis-xxx/
EXCLUDE_PATH_RE = re.compile(
    r"/(v|category|categorie|tag|auteur|author|page|wp-|feed|comments|search|"
    r"mentions-legales|cgu|cgv|contact|a-propos|qui-sommes-nous|"
    r"politique-de-confidentialite|plan-du-site|sitemap)(/|$)",
    re.IGNORECASE,
)

def is_article(url: str) -> bool:
    if "/v/" in url:
        return False
    m = re.match(r"^https?://enseigna\.fr/([^/?#]+)/?$", url)
    if not m:
        return False
    if EXCLUDE_PATH_RE.search(url):
        return False
    return True

rows = []
start_row = 0
PAGE = 25000
while True:
    body = {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "dimensions": ["page"],
        "rowLimit": PAGE,
        "startRow": start_row,
    }
    resp = svc.searchanalytics().query(siteUrl=SITE, body=body).execute()
    batch = resp.get("rows", [])
    if not batch:
        break
    rows.extend(batch)
    if len(batch) < PAGE:
        break
    start_row += PAGE

filtered = []
for r in rows:
    url = r["keys"][0]
    if not is_article(url):
        continue
    filtered.append({
        "url": url,
        "clicks": int(r.get("clicks", 0)),
        "impressions": int(r.get("impressions", 0)),
        "ctr_pct": round(r.get("ctr", 0) * 100, 2),
        "position": round(r.get("position", 0), 2),
    })

filtered.sort(key=lambda x: x["impressions"], reverse=True)

out_dir = Path("output/reports")
out_dir.mkdir(parents=True, exist_ok=True)
out = out_dir / f"enseigna_gsc_16m_{end.isoformat()}.csv"
with out.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["url", "clicks", "impressions", "ctr_pct", "position"])
    w.writeheader()
    w.writerows(filtered)

tot_c = sum(x["clicks"] for x in filtered)
tot_i = sum(x["impressions"] for x in filtered)
print(f"Period: {start} -> {end}")
print(f"Raw pages: {len(rows)} | Articles kept: {len(filtered)}")
print(f"Total clicks: {tot_c} | Total impressions: {tot_i}")
print(f"CSV: {out}")
print("\nTop 20 par impressions:")
for x in filtered[:20]:
    print(f"  {x['impressions']:>7} imp | {x['clicks']:>5} clicks | CTR {x['ctr_pct']:>5}% | pos {x['position']:>5} | {x['url']}")
