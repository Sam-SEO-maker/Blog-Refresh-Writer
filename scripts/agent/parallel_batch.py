"""Préparation parallèle des articles d'un batch.

Ce que ce module parallélise (et ce qu'il ne parallélise pas)
-------------------------------------------------------------
La chaîne d'un article est séquentielle par construction : le brief a besoin du
mot-clé de l'audit, le plan a besoin du brief, la rédaction a besoin du plan, le
QC YTG a besoin du texte fini. Découper CETTE chaîne en agents ne fait rien
gagner : chaque étape attend la précédente.

Ce qui est réellement parallélisable, ce sont les ARTICLES entre eux : ils ne se
dépendent pas. C'est donc l'axe retenu ici — N articles en vol, chacun sur la
chaîne complète et éprouvée.

Découpage des responsabilités
-----------------------------
- **Ce module (Python, parallèle)** : la phase déterministe et coûteuse en I/O —
  fetch WP, audit GSC, SERP/PAA, guide YTG, décision, `generation_prompt.txt`.
  C'est du réseau bloquant, donc un pool de threads suffit (le GIL n'est pas le
  facteur limitant) et le gain est proportionnel à `--parallel`.
- **La rédaction (subagents Claude Code, hors de ce module)** : elle tourne sous
  l'abonnement Max, jamais via l'API payante. Python ne peut pas l'invoquer ;
  ce module produit donc un *plan de travail* (`parallel_batch_plan.json`) que
  l'agent lit pour lancer ses subagents de rédaction en parallèle.

Le quota YTG (15 req/min) est protégé par `CrossProcessRateLimiter`, partagé
entre processus ET entre threads — sans lui, N articles concurrents tirent
N×13 appels/min et prennent des 429 en fin de chaîne, après avoir déjà payé
le fetch, l'audit et la SERP.
"""

from __future__ import annotations

import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger("ParallelBatch")

# Au-delà de ~5 articles simultanés, on sature DataForSEO/GSC sans gagner de
# débit : la phase est bornée par le quota YTG partagé, pas par le CPU.
DEFAULT_PARALLEL = 3
MAX_PARALLEL = 8


@dataclass
class ArticleResult:
    """Résultat de la préparation d'un article (sérialisé dans le plan)."""

    url: str
    site_slug: str
    status: str = "PENDING"          # PREPARED | SKIPPED | FAILED
    reason: str = ""                 # motif du skip/échec, vide si succès
    context_dir: str = ""
    generation_prompt: str = ""
    output_html: str = ""
    output_json: str = ""
    strategy: str = ""
    main_keyword: str = ""
    ytg_guide_id: str = ""
    article_type: str = ""           # avis|versus (enseigna) sinon vide
    assets_before: dict = field(default_factory=dict)
    duration_s: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


# Actions qui sortent du batch : rien à générer.
TERMINAL_ACTIONS = {
    "NO_ACTION",
    "BLOCKED_QUALITY_ISSUES",
    "ERROR",
    "REDIRECT_301_SUGGESTED",
}


class ParallelBatchPreparer:
    """Prépare en parallèle le contexte de plusieurs articles.

    Args:
        orchestrator: instance de `RefreshOrchestrator` déjà configurée.
        parallel: nombre d'articles préparés simultanément (borné à MAX_PARALLEL).
    """

    def __init__(self, orchestrator, parallel: int = DEFAULT_PARALLEL):
        self.orchestrator = orchestrator
        # `parallel or DEFAULT` serait faux pour 0 : 0 est falsy et retomberait
        # sur le défaut au lieu d'être borné à 1.
        requested = DEFAULT_PARALLEL if parallel is None else int(parallel)
        self.parallel = max(1, min(requested, MAX_PARALLEL))
        # `RefreshOrchestrator` porte des clients réutilisés (sheets, analyzers).
        # Les appels Sheets sont sérialisés : l'API Google renvoie du 429 sur des
        # écritures concurrentes, et deux writes simultanés sur la même feuille
        # peuvent se recouvrir.
        self._sheets_lock = threading.Lock()
        self._log_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Préparation d'un article
    # ------------------------------------------------------------------

    def _prepare_one(self, row, prepare_fn: Callable) -> ArticleResult:
        """Exécute la phase déterministe pour un article. Ne lève jamais.

        Un article qui échoue ne doit pas faire tomber le lot : l'erreur est
        capturée et reportée dans le plan, les autres articles continuent.
        """
        import time as _time

        url = getattr(row, "blogpost_url", "") or ""
        site_slug = getattr(row, "site_slug", "") or ""
        started = _time.monotonic()

        try:
            outcome = prepare_fn(row, self._sheets_lock)

            action = (outcome.get("action") or "").upper()
            if action in TERMINAL_ACTIONS:
                return ArticleResult(
                    url=url, site_slug=site_slug, status="SKIPPED",
                    reason=action, duration_s=_time.monotonic() - started,
                )

            return ArticleResult(
                url=url,
                site_slug=site_slug,
                status="PREPARED",
                context_dir=str(outcome.get("context_dir", "")),
                generation_prompt=str(outcome.get("generation_prompt", "")),
                output_html=str(outcome.get("output_html", "")),
                output_json=str(outcome.get("output_json", "")),
                strategy=str(outcome.get("strategy", "")),
                main_keyword=str(outcome.get("main_keyword", "")),
                ytg_guide_id=str(outcome.get("ytg_guide_id", "")),
                article_type=str(outcome.get("article_type", "")),
                assets_before=outcome.get("assets_before") or {},
                duration_s=_time.monotonic() - started,
            )

        except Exception as e:
            with self._log_lock:
                logger.error(f"[PREPARE] {url} — échec : {e}")
            return ArticleResult(
                url=url, site_slug=site_slug, status="FAILED",
                reason=f"{type(e).__name__}: {e}",
                duration_s=_time.monotonic() - started,
            )

    # ------------------------------------------------------------------
    # Fan-out
    # ------------------------------------------------------------------

    def run(self, rows: list, prepare_fn: Callable) -> list[ArticleResult]:
        """Prépare tous les articles avec au plus `self.parallel` en vol.

        Args:
            rows: lignes issues de la Sheet.
            prepare_fn: callable `(row, sheets_lock) -> dict` réalisant la phase
                déterministe d'un article.

        Returns:
            Les résultats dans l'ordre d'entrée (déterminisme du rapport, même
            si l'exécution est concurrente).
        """
        if not rows:
            return []

        logger.info(
            f"[PARALLEL] {len(rows)} article(s), {self.parallel} en vol simultanément"
        )

        results: dict[int, ArticleResult] = {}
        with ThreadPoolExecutor(max_workers=self.parallel) as pool:
            futures = {
                pool.submit(self._prepare_one, row, prepare_fn): idx
                for idx, row in enumerate(rows)
            }
            done = 0
            for fut in as_completed(futures):
                idx = futures[fut]
                results[idx] = fut.result()
                done += 1
                r = results[idx]
                with self._log_lock:
                    icon = {"PREPARED": "[OK]  ", "SKIPPED": "[SKIP]",
                            "FAILED": "[FAIL]"}.get(r.status, "[?]   ")
                    logger.info(
                        f"{icon} ({done}/{len(rows)}) {r.url} "
                        f"{r.reason or r.strategy} — {r.duration_s:.0f}s"
                    )

        return [results[i] for i in range(len(rows))]

    # ------------------------------------------------------------------
    # Plan de travail
    # ------------------------------------------------------------------

    @staticmethod
    def write_plan(results: list[ArticleResult], path: Path) -> Path:
        """Écrit le plan de travail lu ensuite par l'agent pour la rédaction.

        Python s'arrête ici : la génération passe par des subagents Claude Code
        (abonnement Max), qu'un script ne peut pas invoquer. Ce fichier est le
        point de passage entre la phase déterministe et la phase rédactionnelle.
        """
        prepared = [r for r in results if r.status == "PREPARED"]
        payload = {
            "summary": {
                "total": len(results),
                "prepared": len(prepared),
                "skipped": sum(1 for r in results if r.status == "SKIPPED"),
                "failed": sum(1 for r in results if r.status == "FAILED"),
            },
            "articles": [r.to_dict() for r in results],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return path
