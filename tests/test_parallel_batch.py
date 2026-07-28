"""Tests de la préparation parallèle du batch et du quota YTG partagé.

Enjeu couvert ici : sans décompte partagé entre processus, N articles en
parallèle tirent chacun jusqu'au plafond et prennent des 429 — l'article échoue
en toute fin de chaîne, après avoir déjà payé le fetch WP, l'audit GSC, la SERP
et la génération. Ces tests verrouillent l'invariant.
"""

import time
from multiprocessing import Process, Queue

import pytest

from _shared.core.cross_process_rate_limit import CrossProcessRateLimiter
from scripts.agent.parallel_batch import (
    ArticleResult,
    MAX_PARALLEL,
    ParallelBatchPreparer,
    TERMINAL_ACTIONS,
)


def _quota_worker(state_dir, q):
    """Worker du test multi-processus (doit être au niveau module : picklable)."""
    lim = CrossProcessRateLimiter(
        name="shared", max_calls=3, window=3.0, state_dir=state_dir
    )
    stamps = []
    for _ in range(3):
        lim.wait_if_needed()
        stamps.append(time.time())
    q.put(stamps)


# ---------------------------------------------------------------------------
# Rate limiter partagé
# ---------------------------------------------------------------------------

class TestCrossProcessRateLimiter:

    def test_allows_calls_under_the_cap(self, tmp_path):
        lim = CrossProcessRateLimiter(name="t", max_calls=5, window=60.0, state_dir=tmp_path)
        for _ in range(5):
            assert lim.wait_if_needed() == 0.0  # aucun blocage sous le plafond
        assert lim.current_usage() == 5

    def test_blocks_when_cap_reached(self, tmp_path):
        lim = CrossProcessRateLimiter(name="t", max_calls=2, window=2.0, state_dir=tmp_path)
        lim.wait_if_needed()
        lim.wait_if_needed()
        waited = lim.wait_if_needed()  # 3e appel : doit attendre l'expiration
        assert waited > 0

    def test_window_slides(self, tmp_path):
        lim = CrossProcessRateLimiter(name="t", max_calls=2, window=1.0, state_dir=tmp_path)
        lim.wait_if_needed()
        lim.wait_if_needed()
        time.sleep(1.2)  # la fenêtre expire
        assert lim.current_usage() == 0
        assert lim.wait_if_needed() == 0.0

    def test_corrupted_state_does_not_wedge_the_batch(self, tmp_path):
        lim = CrossProcessRateLimiter(name="t", max_calls=2, window=60.0, state_dir=tmp_path)
        lim.wait_if_needed()
        lim.state_path.write_text("{ this is not json", encoding="utf-8")
        # Un crash en pleine écriture ne doit pas bloquer indéfiniment le lot.
        assert lim.wait_if_needed() == 0.0

    def test_quota_is_shared_across_processes(self, tmp_path):
        """Le cœur du sujet : deux processus ne doivent pas doubler le quota."""
        q = Queue()
        procs = [Process(target=_quota_worker, args=(tmp_path, q)) for _ in range(2)]
        for p in procs:
            p.start()
        stamps = []
        for _ in procs:
            stamps.extend(q.get())
        for p in procs:
            p.join(timeout=30)

        stamps.sort()
        assert len(stamps) == 6
        # Invariant : jamais plus de 3 appels dans une fenêtre glissante de 3s,
        # alors que 2 processus non coordonnés en auraient permis 6.
        worst = max(
            sum(1 for u in stamps if t - 3.0 < u <= t)
            for t in stamps
        )
        assert worst <= 3, f"quota dépassé : {worst} appels dans la fenêtre"


# ---------------------------------------------------------------------------
# Préparation parallèle
# ---------------------------------------------------------------------------

class _Row:
    def __init__(self, url, site_slug="superprof.fr-ressources"):
        self.blogpost_url = url
        self.site_slug = site_slug
        self.main_keyword = "kw"
        self.title = "T"
        self.post_type = "STANDALONE"
        self.people_also_ask = ""
        self.secondary_keywords = ""


class TestParallelBatchPreparer:

    def test_parallel_is_clamped_to_bounds(self):
        assert ParallelBatchPreparer(None, parallel=99).parallel == MAX_PARALLEL
        assert ParallelBatchPreparer(None, parallel=0).parallel == 1

    def test_results_keep_input_order(self):
        """L'exécution est concurrente, le rapport doit rester déterministe."""
        rows = [_Row(f"https://x.test/a{i}") for i in range(6)]

        def prepare_fn(row, lock):
            # Inverser les durées : le dernier finit en premier.
            idx = int(row.blogpost_url[-1])
            time.sleep((6 - idx) * 0.01)
            return {"action": "FULL_REFRESH", "strategy": "FULL_REFRESH"}

        results = ParallelBatchPreparer(None, parallel=4).run(rows, prepare_fn)
        assert [r.url for r in results] == [r.blogpost_url for r in rows]

    def test_one_failure_does_not_sink_the_batch(self):
        rows = [_Row(f"https://x.test/a{i}") for i in range(4)]

        def prepare_fn(row, lock):
            if row.blogpost_url.endswith("a2"):
                raise RuntimeError("WP fetch failed")
            return {"action": "FULL_REFRESH", "strategy": "FULL_REFRESH"}

        results = ParallelBatchPreparer(None, parallel=3).run(rows, prepare_fn)
        assert sum(1 for r in results if r.status == "PREPARED") == 3
        failed = [r for r in results if r.status == "FAILED"]
        assert len(failed) == 1
        assert "WP fetch failed" in failed[0].reason

    @pytest.mark.parametrize("action", sorted(TERMINAL_ACTIONS))
    def test_terminal_actions_are_skipped_not_generated(self, action):
        rows = [_Row("https://x.test/a")]

        def prepare_fn(row, lock):
            return {"action": action}

        results = ParallelBatchPreparer(None, parallel=1).run(rows, prepare_fn)
        assert results[0].status == "SKIPPED"
        assert results[0].reason == action

    def test_concurrency_never_exceeds_the_cap(self):
        """Le plafond demandé doit être un vrai plafond, pas une indication."""
        rows = [_Row(f"https://x.test/a{i}") for i in range(12)]
        import threading
        in_flight = 0
        peak = 0
        lock = threading.Lock()

        def prepare_fn(row, sheets_lock):
            nonlocal in_flight, peak
            with lock:
                in_flight += 1
                peak = max(peak, in_flight)
            time.sleep(0.02)
            with lock:
                in_flight -= 1
            return {"action": "FULL_REFRESH"}

        ParallelBatchPreparer(None, parallel=3).run(rows, prepare_fn)
        assert peak <= 3, f"{peak} articles en vol pour un plafond de 3"

    def test_plan_is_written_with_summary(self, tmp_path):
        import json

        results = [
            ArticleResult(url="u1", site_slug="s", status="PREPARED"),
            ArticleResult(url="u2", site_slug="s", status="SKIPPED", reason="NO_ACTION"),
            ArticleResult(url="u3", site_slug="s", status="FAILED", reason="boom"),
        ]
        path = ParallelBatchPreparer.write_plan(results, tmp_path / "plan.json")
        payload = json.loads(path.read_text(encoding="utf-8"))

        assert payload["summary"] == {"total": 3, "prepared": 1, "skipped": 1, "failed": 1}
        assert len(payload["articles"]) == 3
