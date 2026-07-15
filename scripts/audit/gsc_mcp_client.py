"""Client MCP `gsc-remote` en pur `requests` (Phase 6c — bascule fetch GSC).

Le serveur `gsc-remote` (http://mcp.superprof.cloud:3001/sse) parle MCP sur
SSE + JSON-RPC. `supergateway` n'est qu'un pont stdio↔SSE pour Claude Code ; le
serveur lui-même est joignable directement en HTTP, sans authentification. Ce
client permet donc à `GSCAnalyzer` de lire GSC via le MCP **depuis le process
Python**, sans dépendance nouvelle (pas de SDK `mcp`, pas d'asyncio).

Les tools MCP renvoient des **tableaux texte pré-formatés** (pas du JSON). On les
reparse en lignes {query, clicks, impressions, ctr, position} pour rester
iso-contrat avec l'API directe (cf. GSC_MCP_POC_FINDINGS.md : 0 divergence).

Usage :
    client = GSCMCPClient()
    rows = client.search_by_page_query(site_url, page_url, days=30)

Le client est synchrone et jetable (une session SSE par appel — simple et
robuste ; pas de connexion longue à gérer). En cas d'indisponibilité réseau, les
méthodes lèvent `GSCMCPError` : l'appelant (`GSCAnalyzer`) retombe sur le SA.
"""
from __future__ import annotations

import json
import os
import queue
import re
import threading
import time
from typing import Optional

import requests

DEFAULT_BASE_URL = os.environ.get("GSC_MCP_BASE_URL", "http://mcp.superprof.cloud:3001")
_PROTOCOL_VERSION = "2024-11-05"


class GSCMCPError(RuntimeError):
    """Erreur d'accès au MCP gsc-remote (réseau, protocole, tool). L'appelant
    doit retomber sur le service account."""


class GSCMCPClient:
    """Client synchrone minimal du serveur MCP gsc-remote (SSE + JSON-RPC)."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # -- protocole bas niveau -------------------------------------------------

    def _call_tool(self, name: str, arguments: dict) -> str:
        """Ouvre une session SSE, initialise, appelle un tool, retourne le texte.

        Lève GSCMCPError sur tout échec (réseau, timeout, erreur JSON-RPC).
        """
        msgs: "queue.Queue[dict]" = queue.Queue()
        endpoint: dict = {}
        stop = threading.Event()

        def reader():
            try:
                r = requests.get(self.base_url + "/sse", stream=True, timeout=self.timeout)
                # text/event-stream sans charset → requests tombe en latin-1 et
                # corromprait les accents (ex: "3ème" → "3Ã¨me"). Forcer UTF-8.
                r.encoding = "utf-8"
                event = None
                for raw in r.iter_lines(decode_unicode=True):
                    if stop.is_set():
                        break
                    if raw is None:
                        continue
                    line = raw.strip()
                    if line.startswith("event:"):
                        event = line[len("event:"):].strip()
                    elif line.startswith("data:"):
                        data = line[len("data:"):].strip()
                        if event == "endpoint":
                            endpoint["url"] = self.base_url + data
                        else:
                            try:
                                msgs.put(json.loads(data))
                            except Exception:
                                pass
                    elif line == "":
                        event = None
            except Exception as e:  # noqa: BLE001 — remonté via la queue sentinelle
                endpoint["error"] = str(e)

        t = threading.Thread(target=reader, daemon=True)
        t.start()
        try:
            post_url = self._await_endpoint(endpoint)

            self._post(post_url, "initialize", _id=1, params={
                "protocolVersion": _PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "content-writer-gsc", "version": "1.0"},
            })
            init = self._await_id(msgs, 1)
            if not init or "result" not in init:
                raise GSCMCPError("initialize MCP échoué")
            self._post(post_url, "notifications/initialized")

            self._post(post_url, "tools/call", _id=2, params={
                "name": name, "arguments": arguments,
            })
            res = self._await_id(msgs, 2, timeout=self.timeout + 15)
            if not res or "result" not in res:
                raise GSCMCPError(f"tools/call {name} échoué : {json.dumps(res)[:200] if res else 'no response'}")

            content = res["result"].get("content", [])
            if content and isinstance(content, list) and content[0].get("type") == "text":
                return content[0].get("text", "")
            raise GSCMCPError(f"réponse MCP inattendue pour {name}")
        finally:
            stop.set()

    def _await_endpoint(self, endpoint: dict, tries: int = 60) -> str:
        for _ in range(tries):
            if "url" in endpoint:
                return endpoint["url"]
            if "error" in endpoint:
                raise GSCMCPError(f"connexion SSE échouée : {endpoint['error']}")
            time.sleep(0.1)
        raise GSCMCPError("endpoint SSE non reçu (timeout)")

    def _post(self, post_url: str, method: str, _id: Optional[int] = None,
              params: Optional[dict] = None) -> None:
        payload = {"jsonrpc": "2.0", "method": method}
        if _id is not None:
            payload["id"] = _id
        if params is not None:
            payload["params"] = params
        try:
            requests.post(post_url, json=payload, timeout=self.timeout)
        except requests.RequestException as e:
            raise GSCMCPError(f"POST {method} échoué : {e}") from e

    @staticmethod
    def _await_id(msgs: "queue.Queue[dict]", _id: int, timeout: int = 30) -> Optional[dict]:
        end = time.time() + timeout
        while time.time() < end:
            try:
                m = msgs.get(timeout=max(0.1, end - time.time()))
            except queue.Empty:
                return None
            if m.get("id") == _id:
                return m
        return None

    # -- API haut niveau ------------------------------------------------------

    def search_by_page_query(self, site_url: str, page_url: str, days: int = 30) -> list[dict]:
        """Perf 30j par requête d'une URL (équivalent GSCAnalyzer direct).

        Retourne des lignes {query, clicks, impressions, ctr, position} triées
        clics DESC. Lève GSCMCPError si le MCP est indisponible.
        """
        text = self._call_tool("get_search_by_page_query", {
            "site_url": site_url, "page_url": page_url, "days": days,
        })
        return parse_query_table(text)


# -- parsing des tableaux texte MCP ------------------------------------------

_ROW_RE = re.compile(
    r"^(?P<query>.+?)\s*\|\s*(?P<clicks>[\d.,]+)\s*\|\s*(?P<impr>[\d.,]+)\s*\|\s*"
    r"(?P<ctr>[\d.,]+)%\s*\|\s*(?P<pos>[\d.,]+)\s*$"
)


def _num(s: str) -> float:
    return float(s.replace(",", "").strip())


def parse_query_table(text: str) -> list[dict]:
    """Parse le tableau texte `Query | Clicks | Impressions | CTR | Position`.

    Ignore l'en-tête, les séparateurs, et la ligne TOTAL. Robuste aux requêtes
    contenant des chiffres (le regex ancre sur les 4 dernières colonnes).
    """
    rows: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("Query ") or set(line) <= {"-"}:
            continue
        if line.upper().startswith("TOTAL"):
            continue
        m = _ROW_RE.match(line)
        if not m:
            continue
        rows.append({
            "query": m.group("query").strip(),
            "clicks": int(_num(m.group("clicks"))),
            "impressions": int(_num(m.group("impr"))),
            "ctr": round(_num(m.group("ctr")), 2),
            "position": round(_num(m.group("pos")), 1),
        })
    rows.sort(key=lambda r: (-r["clicks"], -r["impressions"]))
    return rows
