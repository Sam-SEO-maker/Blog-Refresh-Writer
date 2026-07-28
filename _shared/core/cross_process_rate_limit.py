"""Rate limiter à fenêtre glissante partagé ENTRE PROCESSUS.

Pourquoi ce module existe
-------------------------
`scripts/audit/ytg_corrector.RateLimiter` tient ses timestamps en mémoire. Tant
que le batch était séquentiel (un seul `cw finalize` à la fois), un compteur par
processus suffisait : personne d'autre ne consommait le quota en même temps.

Dès qu'on lance N articles en parallèle (`/batch --parallel N`), chaque processus
démarre avec un compteur vierge et ignore les appels des autres. Avec le plafond
YTG de 15 req/min, 3 processus qui se croient seuls tirent jusqu'à 39 appels/min
et prennent des 429 — l'article échoue en fin de chaîne, après avoir déjà payé le
fetch WP, l'audit GSC, la SERP et la génération.

Ce limiter déplace donc la fenêtre glissante dans un fichier d'état verrouillé
(`fcntl.flock`, exclusif) : tous les processus de la machine partagent le même
décompte, quel que soit leur nombre.

Portée : une seule machine (verrou fichier POSIX). C'est exactement le périmètre
du batch, qui tourne en local chez un SEO Manager.
"""

from __future__ import annotations

import errno
import fcntl
import json
import os
import time
from pathlib import Path
from typing import Optional

# Le plafond réel de l'API YTG est de 15 req/min. On vise 13 pour garder une
# marge : l'horloge du serveur n'est pas la nôtre, et un appel parti à t+59.9s
# peut être compté dans la minute suivante côté YTG.
DEFAULT_MAX_CALLS = 13
DEFAULT_WINDOW = 60.0

# État hors du repo : c'est du runtime, jamais du versionné.
DEFAULT_STATE_DIR = Path.home() / ".cache" / "content-writer" / "ratelimit"


class CrossProcessRateLimiter:
    """Fenêtre glissante partagée entre processus via un fichier verrouillé.

    Interface volontairement identique à `RateLimiter.wait_if_needed()` pour
    pouvoir remplacer l'un par l'autre sans toucher aux appelants.

    Usage::

        limiter = CrossProcessRateLimiter(name="ytg")
        limiter.wait_if_needed()   # bloque tant que le quota partagé est saturé
        ... appel API ...
    """

    def __init__(
        self,
        name: str = "ytg",
        max_calls: int = DEFAULT_MAX_CALLS,
        window: float = DEFAULT_WINDOW,
        state_dir: Optional[Path] = None,
    ):
        self.name = name
        self.max_calls = max_calls
        self.window = window
        state_dir = Path(state_dir) if state_dir else DEFAULT_STATE_DIR
        state_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = state_dir / f"{name}.json"

    # ------------------------------------------------------------------
    # Verrou
    # ------------------------------------------------------------------

    def _read_timestamps(self, fh) -> list[float]:
        """Lit les timestamps depuis un descripteur déjà verrouillé."""
        try:
            fh.seek(0)
            raw = fh.read()
            if not raw.strip():
                return []
            data = json.loads(raw)
            return [float(t) for t in data.get("timestamps", [])]
        except (json.JSONDecodeError, ValueError, TypeError):
            # État corrompu (crash en pleine écriture) : repartir de zéro est
            # sûr côté quota — au pire on autorise une fenêtre trop permissive
            # une seule fois, plutôt que de bloquer le batch indéfiniment.
            return []

    def _write_timestamps(self, fh, timestamps: list[float]) -> None:
        fh.seek(0)
        fh.truncate()
        json.dump({"timestamps": timestamps}, fh)
        fh.flush()
        os.fsync(fh.fileno())

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def wait_if_needed(self, logger=None) -> float:
        """Bloque jusqu'à ce qu'un créneau soit libre, puis réserve ce créneau.

        Retourne le temps réellement attendu (secondes), utile pour les logs et
        les tests.

        Le verrou est relâché PENDANT l'attente : sinon le premier processus en
        attente bloquerait tous les autres, y compris ceux dont le créneau se
        libère avant le sien.
        """
        total_waited = 0.0

        while True:
            with open(self.state_path, "a+", encoding="utf-8") as fh:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
                try:
                    now = time.time()
                    timestamps = [t for t in self._read_timestamps(fh) if now - t < self.window]

                    if len(timestamps) < self.max_calls:
                        # Créneau libre : on le réserve immédiatement, sous
                        # verrou, pour qu'aucun autre processus ne le prenne.
                        timestamps.append(now)
                        self._write_timestamps(fh, timestamps)
                        return total_waited

                    # Saturé : calculer l'attente jusqu'à expiration du plus
                    # ancien appel, puis relâcher le verrou avant de dormir.
                    sleep_time = self.window - (now - min(timestamps)) + 0.5
                finally:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

            sleep_time = max(0.1, sleep_time)
            if logger is not None:
                logger.info(
                    f"[RateLimit:{self.name}] quota partagé saturé "
                    f"({self.max_calls}/{self.window:.0f}s) — attente {sleep_time:.0f}s"
                )
            time.sleep(sleep_time)
            total_waited += sleep_time

    def reset(self) -> None:
        """Vide la fenêtre. Réservé aux tests et au débogage."""
        try:
            self.state_path.unlink()
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise

    def current_usage(self) -> int:
        """Nombre d'appels dans la fenêtre courante (lecture seule, diagnostic)."""
        if not self.state_path.exists():
            return 0
        with open(self.state_path, "a+", encoding="utf-8") as fh:
            fcntl.flock(fh.fileno(), fcntl.LOCK_SH)
            try:
                now = time.time()
                return len([t for t in self._read_timestamps(fh) if now - t < self.window])
            finally:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
