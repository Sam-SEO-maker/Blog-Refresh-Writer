"""
Superprof Landing Rotator

Sélectionne intelligemment la landing Superprof + ancre pour chaque article,
en variant les URLs et ancres pour faire gagner des positions de KW à Superprof.

Logique de sélection :
1. Filtre les landings par sujet (yoga vs pilates vs ashtanga, etc.)
2. Sélection pondérée par poids (weight) + bonus KW P2-P10
3. Anti-répétition : consulte l'historique des landings utilisées récemment
4. Ancre aléatoire dans le pool de la landing sélectionnée
"""

import json
import random
import hashlib
from pathlib import Path
from typing import Optional


SUPERPROF_BASE_URL = "https://www.superprof.fr"
CONFIG_PATH = Path(__file__).resolve().parents[2] / "_shared" / "config" / "superprof_landings.json"

# Contextes géographiques pour amener naturellement la ville dans le CTA
GEO_CONTEXTS = {
    "paris": [
        "La capitale regorge de professionnels expérimentés.",
        "En région parisienne, l'offre ne manque pas.",
        "À Paris, la communauté {discipline} est particulièrement riche.",
    ],
    "lyon": [
        "Du côté de Lyon, la communauté {discipline} est particulièrement active.",
        "Si vous êtes dans la région lyonnaise, vous trouverez facilement un accompagnement.",
        "Lyon compte de nombreux professionnels passionnés.",
    ],
    "marseille": [
        "Dans le sud, et notamment à Marseille, la pratique se développe.",
        "Vous êtes en région marseillaise ?",
        "À Marseille, l'offre de {discipline} s'est étoffée ces dernières années.",
    ],
    "toulouse": [
        "En région toulousaine ? L'offre de {discipline} s'est étoffée ces dernières années.",
        "Toulouse propose un beau réseau de professionnels dans ce domaine.",
    ],
    "nantes": [
        "Du côté de Nantes, plusieurs professionnels proposent un accompagnement individuel.",
        "L'offre nantaise en {discipline} s'est développée.",
    ],
    "online": [
        "Où que vous soyez en France, un accompagnement à distance reste une option efficace.",
        "Pas de professeur près de chez vous ? La visio est une alternative qui a fait ses preuves.",
        "Le format en ligne permet d'accéder aux meilleurs professionnels sans contrainte géographique.",
    ],
    "france": [
        "Partout en France, il est possible de trouver un accompagnement adapté.",
        "De nombreux professionnels proposent leurs services à domicile ou en visio.",
    ],
}

# Max occurrences d'une même ancre exacte sur l'ensemble des articles voisins
MAX_ANCHOR_REPEATS = 3


class SuperprofRotator:
    """Rotation intelligente des landings et ancres CTA Superprof."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or CONFIG_PATH
        self._config = self._load_config()

    def _load_config(self) -> dict:
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"[SuperprofRotator] Erreur chargement config: {e}")
            return {}

    def select_landing(
        self,
        site_id: str,
        article_subject: str = "",
        article_url: str = "",
        recently_used_slugs: Optional[list[str]] = None,
        recently_used_anchors: Optional[list[str]] = None,
    ) -> dict:
        """
        Sélectionne une landing + ancre pour un article donné.

        Returns:
            {
                "url": "https://www.superprof.fr/cours/yoga/paris/",
                "slug": "/cours/yoga/paris/",
                "anchor": "prof de yoga à Paris",
                "geo_context": "Du côté de Lyon, la communauté yoga est ...",
                "city": "lyon",
                "target_keywords": [...],
                "reason": "Weighted selection (...)"
            }
        """
        site_config = self._config.get(site_id)
        if not site_config:
            return self._fallback(site_id)

        landings = site_config.get("landings", [])
        if not landings:
            return self._fallback(site_id)

        # Matière : article_subject explicite > dérivée de l'URL > défaut du site.
        # (article_subject n'est aujourd'hui jamais peuplé en amont ; l'URL
        # /ressources/{matiere}/... est la source fiable de la matière.)
        subject = (article_subject or "").strip().lower()
        if not subject:
            subject = self._derive_subject_from_url(article_url)
        if not subject:
            subject = site_config.get("default_subject", "")
        matched = [l for l in landings if self._matches_subject(l, subject)]
        # Préférer un match exact de matière (slug == subject) pour éviter qu'une
        # sous-chaîne l'emporte (ex: "physique" matchant un article "physique-chimie").
        exact = [l for l in matched if subject in l.get("subject_match", [])]
        if exact:
            matched = exact
        if not matched:
            matched = landings

        recently_used = set(recently_used_slugs or [])
        weighted = []
        for landing in matched:
            slug = landing["slug"]
            base_weight = landing.get("weight", 10)
            kw_bonus = self._calculate_kw_bonus(landing)
            recency_factor = 0.33 if slug in recently_used else 1.0
            final_weight = (base_weight + kw_bonus) * recency_factor
            weighted.append((landing, final_weight))

        if article_url:
            seed = int(hashlib.md5(article_url.encode()).hexdigest()[:8], 16)
            rng = random.Random(seed)
        else:
            rng = random.Random()

        selected = self._weighted_choice(weighted, rng)

        # Sélection ancre avec plafonnement anti-répétition
        anchor_pool = selected.get("anchor_pool", [])
        anchor = self._select_anchor(
            anchor_pool, subject, recently_used_anchors or [], rng
        )

        slug = selected["slug"]
        kw_bonus = self._calculate_kw_bonus(selected)

        # Extraire la ville du slug et générer le contexte géographique
        city = self._extract_city(slug)
        geo_context = self._generate_geo_context(
            city, subject, rng, selected.get("city_display", "")
        )

        return {
            "url": f"{SUPERPROF_BASE_URL}{slug}",
            "slug": slug,
            "anchor": anchor,
            "city": city,
            "geo_context": geo_context,
            "target_keywords": selected.get("target_keywords", []),
            "reason": (
                f"Weighted selection (subject={subject}, city={city}, "
                f"weight={selected.get('weight', 10)}, kw_bonus={kw_bonus})"
            ),
        }

    def get_prompt_directive(
        self,
        site_id: str,
        article_subject: str = "",
        article_url: str = "",
        recently_used_slugs: Optional[list[str]] = None,
        recently_used_anchors: Optional[list[str]] = None,
    ) -> str:
        """
        Génère la directive prompt pour le CTA Superprof.
        Bloc de texte prêt à injecter dans le prompt de génération.
        Inclut le contexte géographique pour naturaliser l'ancre.
        """
        selection = self.select_landing(
            site_id=site_id,
            article_subject=article_subject,
            article_url=article_url,
            recently_used_slugs=recently_used_slugs,
            recently_used_anchors=recently_used_anchors,
        )

        target_kws = selection.get("target_keywords", [])
        kw_info = ""
        if target_kws:
            top_kws = sorted(
                target_kws,
                key=lambda k: k.get("search_volume", 0),
                reverse=True,
            )[:3]
            kw_lines = [
                f"  - \"{kw['keyword']}\" (P{kw['position']}, SV={kw['search_volume']})"
                for kw in top_kws
            ]
            kw_info = (
                "\n\n**KW cibles Superprof (cette landing)** :\n"
                + "\n".join(kw_lines)
                + "\n→ Le lien aide Superprof à gagner des positions sur ces requêtes."
            )

        # Directive contexte géographique
        geo_context = selection.get("geo_context", "")
        city = selection.get("city", "france")
        geo_directive = ""
        if geo_context:
            geo_directive = (
                f"\n\n**Contexte géographique** : \"{geo_context}\"\n"
                f"→ Utilise cette phrase d'accroche (ou reformule-la naturellement) "
                f"AVANT le lien pour amener la mention de la ville ({city}) "
                f"de façon contextuelle.\n"
                f"→ NE JAMAIS écrire \"Un [ancre avec ville]\" sans contexte "
                f"géographique préalable dans la phrase.\n"
                f"→ Le lecteur doit comprendre POURQUOI on parle de cette ville."
            )

        return (
            f"### CTA Superprof (OBLIGATOIRE)\n"
            f"\n"
            f"**URL exacte** : `{selection['url']}`\n"
            f"**Ancre exacte** : \"{selection['anchor']}\"\n"
            f"\n"
            f"Utilise EXACTEMENT cette URL et cette ancre dans le callout CTA Superprof.\n"
            f"Ne modifie ni l'URL ni l'ancre. Ne génère AUCUNE autre URL Superprof."
            f"{geo_directive}{kw_info}"
        )

    def get_recently_used(
        self, context_dir: Path, limit: int = 10
    ) -> dict:
        """
        Récupère les slugs ET ancres récemment utilisés dans les audit_data.json voisins.

        Returns:
            {"slugs": [...], "anchors": [...]}
        """
        slugs = []
        anchors = []
        if not context_dir or not context_dir.exists():
            return {"slugs": slugs, "anchors": anchors}

        parent = context_dir.parent
        for sibling_dir in sorted(parent.iterdir(), reverse=True):
            if not sibling_dir.is_dir() or sibling_dir == context_dir:
                continue
            audit_file = sibling_dir / "audit_data.json"
            if audit_file.exists():
                try:
                    with open(audit_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    slug = data.get("superprof_landing_used", "")
                    if slug:
                        slugs.append(slug)
                    anchor = data.get("superprof_anchor_used", "")
                    if anchor:
                        anchors.append(anchor)
                except (json.JSONDecodeError, OSError):
                    continue
            if len(slugs) >= limit:
                break
        return {"slugs": slugs, "anchors": anchors}

    def get_recently_used_slugs(
        self, context_dir: Path, limit: int = 10
    ) -> list[str]:
        """Backward-compatible wrapper."""
        return self.get_recently_used(context_dir, limit)["slugs"]

    def get_valid_slugs(self, site_id: str) -> set[str]:
        """Retourne l'ensemble des slugs valides pour un site donné."""
        site_config = self._config.get(site_id, {})
        landings = site_config.get("landings", [])
        return {landing["slug"] for landing in landings}

    def _derive_subject_from_url(self, url: str) -> str:
        """Extrait la matière d'une URL Superprof.

        /ressources/{matiere}/...  (article du blog)  -> {matiere}
        /cours/{matiere}/{ville}/  (landing)          -> {matiere}
        """
        if not url:
            return ""
        parts = [p for p in url.split("/") if p and "." not in p]
        for marker in ("ressources", "cours"):
            if marker in parts:
                i = parts.index(marker)
                if i + 1 < len(parts):
                    return parts[i + 1].lower()
        return ""

    def _normalize_subject(self, article_subject: str, site_config: dict) -> str:
        if article_subject:
            return article_subject.lower().strip()
        return site_config.get("default_subject", "")

    def _matches_subject(self, landing: dict, subject: str) -> bool:
        subject_match = landing.get("subject_match", [])
        if not subject_match:
            return True
        return any(s in subject for s in subject_match)

    def _calculate_kw_bonus(self, landing: dict) -> float:
        """
        Bonus basé sur les KW cibles P2-P10.
        Plus un KW a de volume et est proche du top 10, plus le bonus est élevé.
        """
        bonus = 0.0
        for kw in landing.get("target_keywords", []):
            pos = kw.get("position", 100)
            sv = kw.get("search_volume", 0)
            if pos <= 10:
                position_factor = (11 - pos) / 10
                bonus += (sv / 1000) * position_factor
            elif pos <= 20:
                position_factor = (21 - pos) / 20
                bonus += (sv / 2000) * position_factor
        return round(bonus, 1)

    def _weighted_choice(self, weighted: list[tuple], rng: random.Random):
        if not weighted:
            return {"slug": "/cours/yoga/france/", "anchor_pool": [], "weight": 10}
        total = sum(w for _, w in weighted)
        if total <= 0:
            return weighted[0][0]
        r = rng.uniform(0, total)
        cumulative = 0
        for landing, weight in weighted:
            cumulative += weight
            if r <= cumulative:
                return landing
        return weighted[-1][0]

    @staticmethod
    def normalize_site_id(blog_id: str) -> str:
        """Normalise un blog_id en site_id (retire TLD, www, etc.)."""
        site_id = blog_id.strip().lower()
        # Retirer protocole
        for prefix in ("https://", "http://", "www."):
            if site_id.startswith(prefix):
                site_id = site_id[len(prefix):]
        # Retirer TLD (.fr, .com, .net, .org, etc.)
        for tld in (".fr", ".com", ".net", ".org", ".io", ".co"):
            if site_id.endswith(tld):
                site_id = site_id[: -len(tld)]
                break
        return site_id

    def _extract_city(self, slug: str) -> str:
        """Extrait la ville du slug Superprof. Ex: /cours/yoga/lyon/ → lyon."""
        parts = [p for p in slug.strip("/").split("/") if p]
        if len(parts) >= 3:
            city = parts[-1]
            # "france" est le générique, pas une ville spécifique
            return city
        return "france"

    def _generate_geo_context(
        self,
        city: str,
        subject: str,
        rng: random.Random,
        city_display: str = "",
    ) -> str:
        """Génère une phrase d'accroche géographique pour naturaliser le CTA."""
        city_key = city.lower()
        discipline = subject.replace("-", " ") if subject else "cette discipline"

        if city_key in GEO_CONTEXTS:
            return rng.choice(GEO_CONTEXTS[city_key]).format(discipline=discipline)

        # Ville réelle hors liste : gabarit générique avec son nom d'affichage.
        if city_key and city_key != "france":
            disp = city_display or city.capitalize()
            generic = [
                f"À {disp}, de nombreux profs proposent un accompagnement en {discipline}.",
                f"Du côté de {disp}, l'offre de cours en {discipline} s'est bien développée.",
                f"À {disp}, trouver un accompagnement en {discipline} est devenu simple.",
            ]
            return rng.choice(generic)

        return rng.choice(GEO_CONTEXTS["france"]).format(discipline=discipline)

    def _select_anchor(
        self,
        anchor_pool: list[str],
        subject: str,
        recently_used_anchors: list[str],
        rng: random.Random,
    ) -> str:
        """
        Sélectionne une ancre en évitant celles trop répétées.
        Plafond : MAX_ANCHOR_REPEATS occurrences d'une même ancre exacte.
        """
        if not anchor_pool:
            return f"professeur de {subject}"

        # Compter les occurrences récentes
        from collections import Counter
        anchor_counts = Counter(recently_used_anchors)

        # Filtrer les ancres non saturées
        available = [
            a for a in anchor_pool
            if anchor_counts.get(a, 0) < MAX_ANCHOR_REPEATS
        ]

        if available:
            return rng.choice(available)

        # Si toutes saturées, prendre la moins utilisée
        return min(anchor_pool, key=lambda a: anchor_counts.get(a, 0))

    def _fallback(self, site_id: str) -> dict:
        """Fallback sûr : ne JAMAIS deviner une landing /cours/{matiere}/{ville}/.

        L'ancienne version dérivait la matière du site_id
        ("superprof-ressources".split()[0] -> "superprof"), produisant
        https://www.superprof.fr/cours/superprof/france/ qui renvoie une 404,
        toujours avec la même ancre "professeur particulier". On pointe désormais
        vers la home Superprof (toujours valide) avec une ancre de marque.
        """
        return {
            "url": f"{SUPERPROF_BASE_URL}/",
            "slug": "/",
            "anchor": "Superprof",
            "city": "france",
            "geo_context": "",
            "target_keywords": [],
            "reason": f"Fallback sûr (site '{site_id}' non configuré, pas de landing devinée)",
        }
