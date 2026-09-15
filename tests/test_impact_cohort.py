"""Rapport d'impact mensuel : garde-fous de méthode et de restitution.

Ces tests protègent les décisions qui font la valeur du rapport, pas les
détails d'implémentation. Ils portent sur trois familles :

1. **les fenêtres** — égalité de durée, exclusion du jour de publication,
   refus de mesurer sans recul suffisant ;
2. **la couverture** — refuser un rapport qui tairait la moitié du mois ;
3. **la cohérence skill ↔ template** — la skill `impact-report` interdit
   certaines formulations ; le template HTML ne doit pas les réintroduire.
   Cette divergence s'est déjà produite (« attribuable au travail éditorial »
   proscrit par la skill, écrit par le template) : elle est silencieuse, donc
   testée.
"""

import re
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from scripts.audit.impact_cohort import (
    MIN_COVERAGE_PCT,
    MIN_MATURITY,
    _article_windows,
    _de,
    _maturity_bucket,
    _month_bounds,
    _pushed_dates_from_journal,
    _query_movement,
    _slug_from_url,
)

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / ".claude" / "skills" / "impact-report" / "SKILL.md"
MODULE = REPO / "scripts" / "audit" / "impact_cohort.py"


# ---------------------------------------------------------------------------
# Fenêtres
# ---------------------------------------------------------------------------

def test_windows_have_equal_length():
    """Avant et après doivent couvrir le même nombre de jours.

    C'est l'invariant de la mesure : des durées inégales rendraient les
    volumes de clics incomparables.
    """
    w = _article_windows("2026-08-06", 30, "2026-09-30")
    before = (datetime.strptime(w["before"]["end"], "%Y-%m-%d")
              - datetime.strptime(w["before"]["start"], "%Y-%m-%d")).days
    after = (datetime.strptime(w["after"]["end"], "%Y-%m-%d")
             - datetime.strptime(w["after"]["start"], "%Y-%m-%d")).days
    assert before == after == 29  # 30 jours inclusifs


def test_publication_day_excluded_from_both_windows():
    """Le jour du push porte les deux versions : il n'appartient à aucun côté."""
    w = _article_windows("2026-08-06", 30, "2026-09-30")
    assert w["before"]["end"] == "2026-08-05"
    assert w["after"]["start"] == "2026-08-07"


def test_window_shrinks_to_available_hindsight():
    """Sans 30 jours disponibles, on mesure sur le recul réel, des deux côtés."""
    w = _article_windows("2026-08-25", 30, "2026-09-07")
    assert w["maturity"] == 13
    assert w["before"]["start"] == "2026-08-12"
    assert w["after"]["end"] == "2026-09-07"


def test_article_below_min_maturity_is_not_measured():
    """Un article publié la veille n'est pas mesurable : bruit de recrawl."""
    assert _article_windows("2026-08-31", 30, "2026-09-02") is None


def test_article_published_after_data_end_is_not_measured():
    assert _article_windows("2026-09-15", 30, "2026-09-07") is None


@pytest.mark.parametrize("days,expected", [
    (7, "7-15 jours"), (15, "7-15 jours"),
    (16, "16-25 jours"), (25, "16-25 jours"),
    (26, "26-30 jours"), (30, "26-30 jours"),
])
def test_maturity_buckets(days, expected):
    assert _maturity_bucket(days) == expected


def test_month_bounds_covers_full_month():
    assert _month_bounds("2026-08") == ("2026-08-01", "2026-08-31")
    assert _month_bounds("2026-02") == ("2026-02-01", "2026-02-28")


@pytest.mark.parametrize("url,slug", [
    ("https://x.fr/ressources/svt/a/dorsale.html", "dorsale"),
    ("https://x.fr/ressources/svt/a/dorsale", "dorsale"),
    ("https://x.fr/ressources/svt/a/dorsale/", "dorsale"),
])
def test_slug_extraction(url, slug):
    assert _slug_from_url(url) == slug


@pytest.mark.parametrize("label,expected", [
    ("août 2026", "d'août 2026"),
    ("octobre 2026", "d'octobre 2026"),
    ("mai 2026", "de mai 2026"),
    ("septembre 2026", "de septembre 2026"),
])
def test_elision(label, expected):
    assert _de(label) == expected


# ---------------------------------------------------------------------------
# Couverture
# ---------------------------------------------------------------------------

def test_coverage_threshold_leaves_room_for_a_few_stragglers():
    """Le seuil refuse un rapport amputé sans bloquer sur un article isolé."""
    assert 80 <= MIN_COVERAGE_PCT < 100


def test_report_ready_ten_days_after_period_end():
    """Règle publiée : lancer le 10 du mois suivant, pas le 1er.

    7 jours de recul minimum + 3 jours de latence GSC. Si l'une des deux
    constantes bouge, la règle affichée dans la skill et la commande doit
    bouger avec elle.
    """
    from scripts.audit.impact_cohort import GSC_LAG_DAYS
    end = datetime(2026, 8, 31)
    ready = end + timedelta(days=MIN_MATURITY + GSC_LAG_DAYS)
    assert ready.day == 10 and ready.month == 9


# ---------------------------------------------------------------------------
# Cohérence skill ↔ template
# ---------------------------------------------------------------------------

def _template_prose() -> str:
    """Prose du rapport : le module entier, commentaires exclus.

    Les commentaires citent les formulations proscrites pour expliquer
    pourquoi elles le sont ; seul ce qui atteint le lecteur compte ici.
    """
    src = MODULE.read_text(encoding="utf-8")
    return "\n".join(
        line for line in src.splitlines()
        if not line.lstrip().startswith("#")
    )


def test_skill_exists_and_declares_the_command():
    assert SKILL.exists(), "la skill impact-report est le mode d'emploi du rapport"
    assert "audit impact" in SKILL.read_text(encoding="utf-8")


def test_template_does_not_overclaim_causality():
    """La skill proscrit « attribuable au travail éditorial ».

    Le contrôle écarte la saisonnalité, pas une mise à jour d'algorithme :
    la formulation défendable est « il suit les articles retravaillés ».
    """
    prose = _template_prose()
    assert "attribuable au travail" not in prose
    assert "il suit les articles qui ont été retravaillés" in prose


def test_template_states_the_maturity_reservation():
    """Des reculs inégaux doivent être signalés comme réserve de lecture.

    La formulation « plancher » tenait à la courbe de maturation, retirée du
    rapport avec les autres sections de praticien. La réserve, elle, reste
    obligatoire : sans elle, un lot dont la moitié est immature se lit comme un
    résultat stabilisé et le mois suivant paraîtra contredire celui-ci.
    """
    prose = _template_prose()
    assert "Réserves de lecture" in prose
    assert "sous-évaluées" in prose


def test_template_reports_expected_volumes_not_only_percentages():
    """Le contrefactuel se cite en volumes : « auraient fait N impressions »."""
    prose = _template_prose()
    assert "auraient fait" in prose
    assert "expected_impressions" in prose


def test_reliability_split_ignores_noise():
    """Une variation sous le bruit de mesure n'est pas une victoire.

    Remplace le seuil de faible effectif par vague (le tableau par vague a été
    retiré du rapport). Compter un article à +2 % comme un gain gonflait le taux
    de réussite : 64/76 devenait 59/76 une fois le bruit écarté, et c'est le
    second chiffre qui se défend.
    """
    src = MODULE.read_text(encoding="utf-8")
    assert '(a["impressions_pct"] or 0) > 5' in src
    assert '-5 <= (a["impressions_pct"] or 0) <= 5' in src


def test_skill_documents_every_rendered_section():
    """Chaque <h2> du rapport doit être couvert par la skill.

    Ajouter une section sans la documenter laisserait la skill décrire un
    rapport qui n'existe plus — l'écart que ces tests existent pour empêcher.
    """
    headings = set(re.findall(r"<h2>(.*?)</h2>", MODULE.read_text(encoding="utf-8")))
    skill = SKILL.read_text(encoding="utf-8").lower()
    # Le titre de l'accroche est dynamique (« Le travail de {mois}… ») : il est
    # décrit par le modèle d'accroche, pas par un intitulé fixe.
    expected_keywords = {
        "Vue d'ensemble": "vue d'ensemble",
        "Détail par vague de republication": "par vague",
        "L'effet grandit avec le recul": "par recul",
        "Combien de temps Google met-il à réévaluer ?": "maturation",
        "Par catégorie éditoriale": "par catégorie",
        "Les plus fortes progressions": "progressions",
        "Les articles en recul": "recul",
        "Articles retouchés après leur refresh": "retouchés",
    }
    for h, keyword in expected_keywords.items():
        if any(h in x for x in headings):
            assert keyword in skill, f"section « {h} » non documentée dans la skill"


# ---------------------------------------------------------------------------
# Sources de dates de republication
# ---------------------------------------------------------------------------

def test_journal_keeps_the_latest_publication(tmp_path, monkeypatch):
    """Un article republié deux fois est daté de la SECONDE passe.

    C'est ce qui distingue le journal du backup `{id}_before.json` : ce dernier
    n'est écrit qu'une fois (`if not bkp.exists()`), donc un article repassé
    reste daté de sa passe initiale et son effet est mesuré sur la mauvaise
    fenêtre.
    """
    import scripts.audit.impact_cohort as mod

    backups = tmp_path / "wp_backups"
    backups.mkdir(parents=True)
    (backups / "_publications.jsonl").write_text(
        '{"ts": "2026-08-06T10:00:00", "post_id": 1, "slug": "a", "url": "u"}\n'
        '{"ts": "2026-09-03T09:00:00", "post_id": 1, "slug": "a", "url": "u"}\n'
        '{"ts": "2026-08-19T11:00:00", "post_id": 2, "slug": "b", "url": "v"}\n',
        encoding="utf-8",
    )

    class _Paths:
        def __init__(self, **kw): pass
        def output_dir(self, site): return tmp_path

    monkeypatch.setattr("_shared.core.site_paths.SitePaths", _Paths)
    out = _pushed_dates_from_journal("whatever")
    assert out == {"a": "2026-09-03", "b": "2026-08-19"}


def test_journal_survives_a_corrupt_line(tmp_path, monkeypatch):
    """Une ligne illisible ne doit pas emporter tout le journal.

    Le fichier est écrit en append par des processus concurrents (batch
    parallèle) : une ligne tronquée est un incident attendu, pas une raison de
    perdre les dates de tous les autres articles.
    """
    backups = tmp_path / "wp_backups"
    backups.mkdir(parents=True)
    (backups / "_publications.jsonl").write_text(
        '{"ts": "2026-08-06T10:00:00", "slug": "bon", "post_id": 1}\n'
        '{"ts": "2026-08-07T10:00:00", "slug":\n'
        '\n'
        '{"ts": "2026-08-08T10:00:00", "slug": "autre", "post_id": 2}\n',
        encoding="utf-8",
    )

    class _Paths:
        def __init__(self, **kw): pass
        def output_dir(self, site): return tmp_path

    monkeypatch.setattr("_shared.core.site_paths.SitePaths", _Paths)
    out = _pushed_dates_from_journal("whatever")
    assert out == {"bon": "2026-08-06", "autre": "2026-08-08"}


def test_push_logs_every_publication_not_only_the_first():
    """`push_to_wp` doit journaliser chaque publication réussie.

    Le backup `_before.json` est gardé par `if not bkp.exists()` : s'appuyer
    sur lui seul a fait disparaître du rapport les 58 articles republiés à la
    main après un échec de `cw push` — 43 % du travail d'un mois, sans que la
    couverture ne le signale.
    """
    src = (Path(__file__).resolve().parents[1]
           / "scripts" / "utils" / "push_to_wp.py").read_text(encoding="utf-8")
    assert "_log_publication" in src
    assert "_publications.jsonl" in src
    # Journalisé seulement si la publication a réussi.
    assert 'if res["ok"]:' in src


# ---------------------------------------------------------------------------
# Déplacement sémantique
# ---------------------------------------------------------------------------

def test_query_movement_splits_gained_lost_held():
    before = {"a": {"impressions": 100, "clicks": 2, "position": 8.4},
              "disparue": {"impressions": 30, "clicks": 0, "position": 22.0}}
    after = {"a": {"impressions": 300, "clicks": 5, "position": 5.1},
             "nouvelle": {"impressions": 80, "clicks": 1, "position": 11.2}}
    m = _query_movement(before, after, 10)

    assert [x["query"] for x in m["gained"]] == ["nouvelle"]
    assert [x["query"] for x in m["lost"]] == ["disparue"]
    assert [x["query"] for x in m["held"]] == ["a"]
    assert m["counts"] == {"gained": 1, "lost": 1, "held": 1,
                           "before": 2, "after": 2}


def test_query_movement_reads_position_gain_the_right_way():
    """Passer de 12 à 7 est un GAIN de 5, pas une perte.

    Le delta est stocké déjà retourné : un rendu qui afficherait le signe brut
    ferait lire une remontée de classement comme un recul.
    """
    m = _query_movement(
        {"q": {"impressions": 10, "clicks": 0, "position": 12.0}},
        {"q": {"impressions": 20, "clicks": 1, "position": 7.0}},
        5,
    )
    assert m["held"][0]["position_delta"] == 5.0


def test_lost_queries_are_ranked_on_their_former_volume():
    """Une requête perdue n'a plus de volume « après ».

    La trier sur les impressions d'après les mettrait toutes à zéro et rendrait
    le top arbitraire — or c'est la seule liste actionnable du rapport.
    """
    before = {
        "grosse": {"impressions": 500, "clicks": 3, "position": 6.0},
        "petite": {"impressions": 5, "clicks": 0, "position": 30.0},
    }
    m = _query_movement(before, {}, 10)
    assert [x["query"] for x in m["lost"]] == ["grosse", "petite"]
