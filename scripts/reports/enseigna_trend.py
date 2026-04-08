"""Compare GSC enseigna.fr - 8 derniers mois vs 8 mois precedents."""
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

load_dotenv()
creds = service_account.Credentials.from_service_account_file(
    str(Path(os.environ["GOOGLE_SA_PATH"]).expanduser()),
    scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
)
svc = build("searchconsole", "v1", credentials=creds)
SITE = "https://enseigna.fr/"

end = datetime.now().date()
mid = end - timedelta(days=243)
start = end - timedelta(days=487)

EXCLUDE = re.compile(r"/(v|category|categorie|tag|auteur|author|page|wp-|feed|comments|search|mentions-legales|cgu|cgv|contact|a-propos|qui-sommes-nous|politique-de-confidentialite|plan-du-site|sitemap)(/|$)", re.I)
def is_article(u):
    if "/v/" in u: return False
    if not re.match(r"^https?://enseigna\.fr/[^/?#]+/?$", u): return False
    return not EXCLUDE.search(u)

def fetch(d1, d2):
    out, sr = {}, 0
    while True:
        r = svc.searchanalytics().query(siteUrl=SITE, body={
            "startDate": d1.isoformat(), "endDate": d2.isoformat(),
            "dimensions": ["page"], "rowLimit": 25000, "startRow": sr,
        }).execute()
        rows = r.get("rows", [])
        if not rows: break
        for row in rows:
            u = row["keys"][0]
            if is_article(u):
                out[u] = (int(row.get("clicks",0)), int(row.get("impressions",0)),
                          row.get("ctr",0)*100, row.get("position",0))
        if len(rows) < 25000: break
        sr += 25000
    return out

print(f"Periode A (recente): {mid} -> {end}")
print(f"Periode B (precedente): {start} -> {mid}")
A = fetch(mid, end)
B = fetch(start, mid)

# Site totals
ta = (sum(v[0] for v in A.values()), sum(v[1] for v in A.values()))
tb = (sum(v[0] for v in B.values()), sum(v[1] for v in B.values()))
print(f"\n=== TOTAL SITE (articles uniquement) ===")
print(f"Periode A: {ta[0]:>6} clicks | {ta[1]:>9} imp")
print(f"Periode B: {tb[0]:>6} clicks | {tb[1]:>9} imp")
print(f"Delta clicks: {(ta[0]-tb[0])/tb[0]*100:+.1f}%  |  Delta imp: {(ta[1]-tb[1])/tb[1]*100:+.1f}%")

# Per-URL declines
declines = []
for u, (ca, ia, ctra, pa) in A.items():
    if u not in B: continue
    cb, ib, ctrb, pb = B[u]
    if ib < 500: continue
    dc = (ca - cb) / cb * 100 if cb else 0
    di = (ia - ib) / ib * 100 if ib else 0
    dp = pa - pb  # positif = chute (position plus haute = pire)
    declines.append((u, cb, ca, dc, ib, ia, di, pb, pa, dp))

declines.sort(key=lambda x: x[3])  # par chute clics

print(f"\n=== TOP 15 CHUTES CLICS (>500 imp) ===")
print(f"{'CL_B':>5} {'CL_A':>5} {'%clk':>7} {'IMP_B':>7} {'IMP_A':>7} {'%imp':>7} {'pos_B':>5} {'pos_A':>5} {'dpos':>6}  URL")
for u, cb, ca, dc, ib, ia, di, pb, pa, dp in declines[:15]:
    print(f"{cb:>5} {ca:>5} {dc:>+7.1f} {ib:>7} {ia:>7} {di:>+7.1f} {pb:>5.1f} {pa:>5.1f} {dp:>+6.1f}  {u}")

print(f"\n=== TOP 10 GAINS CLICS ===")
for u, cb, ca, dc, ib, ia, di, pb, pa, dp in sorted(declines, key=lambda x: -x[3])[:10]:
    print(f"{cb:>5} {ca:>5} {dc:>+7.1f} {ib:>7} {ia:>7} {di:>+7.1f} {pb:>5.1f} {pa:>5.1f} {dp:>+6.1f}  {u}")
