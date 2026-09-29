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
    DIAGS,
    MIN_COVERAGE_PCT,
    MIN_MATURITY,
    YOY_OFFSET_DAYS,
    _article_windows,
    _de,
    _diagnose,
    _month_bounds,
    _net_cell,
    _pos,
    _pos_cell,
    _pushed_dates_from_journal,
    _pl,
    _query_movement,
    _query_reading,
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
    volumes de clics incomparables. Vrai aussi bien en année-sur-année
    qu'avant ce changement, puisque les deux fenêtres restent calées sur la
    même durée N, seule leur ancre (J-365 contre `pushed`) diffère.
    """
    w = _article_windows("2026-08-06", 30, "2026-09-30")
    before = (datetime.strptime(w["before"]["end"], "%Y-%m-%d")
              - datetime.strptime(w["before"]["start"], "%Y-%m-%d")).days
    after = (datetime.strptime(w["after"]["end"], "%Y-%m-%d")
             - datetime.strptime(w["after"]["start"], "%Y-%m-%d")).days
    assert before == after == 29  # 30 jours inclusifs


def test_before_window_anchored_a_year_earlier():
    """« Avant » suit désormais la même date un an plus tôt, pas les jours

    qui précèdent la republication. Pour une republication le 6 août 2026,
    « avant » démarre le lendemain du 6 août 2025 : même décalage d'un jour
    que « après » démarre le lendemain de la republication elle-même.
    """
    w = _article_windows("2026-08-06", 30, "2026-09-30")
    assert w["before"]["start"] == "2025-08-07"
    assert w["before"]["end"] == "2025-09-05"
    assert w["after"]["start"] == "2026-08-07"
    assert w["after"]["end"] == "2026-09-05"


def test_window_shrinks_to_available_hindsight():
    """Sans 30 jours disponibles côté « après », N se réduit des deux côtés.

    Le recul « avant » (J-365) est presque toujours disponible dans
    l'historique GSC : c'est le recul « après », qui dépend de la date de
    republication dans le mois, qui continue de plafonner N.
    """
    w = _article_windows("2026-08-25", 30, "2026-09-07")
    assert w["maturity"] == 13
    assert w["before"]["start"] == "2025-08-26"
    assert w["before"]["end"] == "2025-09-07"
    assert w["after"]["end"] == "2026-09-07"


def test_article_below_min_maturity_is_not_measured():
    """Un article publié la veille n'est pas mesurable : bruit de recrawl."""
    assert _article_windows("2026-08-31", 30, "2026-09-02") is None


def test_article_published_after_data_end_is_not_measured():
    assert _article_windows("2026-09-15", 30, "2026-09-07") is None


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

    La mesure compare un article à lui-même un an plus tôt : elle n'écarte ni
    une mise à jour d'algorithme, ni une évolution de la demande. Revendiquer
    la causalité dans la prose du rapport est donc indéfendable, quelle que
    soit la formulation retenue par ailleurs.

    Le test ne fige plus une phrase précise : celle qui portait cette garantie
    (« il suit les articles qui ont été retravaillés ») justifiait l'écart au
    groupe de contrôle, retiré du rendu avec la notion d'écart net. La
    garantie, elle, reste — et c'est elle qu'on teste.
    """
    prose = _template_prose()
    for banned in ("attribuable au travail", "grâce au refresh",
                   "prouve que", "démontre que"):
        assert banned not in prose, f"causalité surjouée : « {banned} »"


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


def test_template_reports_raw_volumes_not_only_percentages():
    """Les chiffres se citent en volumes, pas seulement en pourcentages.

    « +153 % de clics » sur 84 → 213 clics est vrai et modeste : le
    pourcentage seul surpromet, et c'est par là qu'un rapport se fait
    attaquer. Le verdict doit donc porter les volumes bruts des deux années.

    Le contrefactuel du groupe de contrôle (« auraient fait N impressions »)
    a été retiré du rendu : on refresh précisément les articles dont le trafic
    est atone, donc un écart avec le reste du site est attendu par
    construction et n'apprenait rien. Ce sont les volumes réels qui restent.
    """
    prose = _template_prose()
    assert "impressions_before" in prose
    assert "impressions_after" in prose
    assert "clicks_before" in prose
    assert "clicks_after" in prose


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
        "Réussite selon le recul de mesure": "gradient de recul",
        "Situer ce résultat": "situer ce résultat",
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


# ---------------------------------------------------------------------------
# Diagnostic par article
# ---------------------------------------------------------------------------

def _article(net, maturity, gained, lost, held, before=100, after=100):
    return {
        "maturity": maturity,
        "net_impressions_pct": net,
        "before": {"impressions": before},
        "after": {"impressions": after},
        "queries": {"counts": {"gained": gained, "lost": lost, "held": held}},
    }


def test_a_declining_article_never_gets_a_positive_label():
    """Le garde-fou qui a motivé l'étiquette « audience resserrée ».

    `gagnées > maintenues` est vrai trivialement quand l'article tient peu de
    requêtes. Sur le lot réel, `forces-et-effets` (+1 gagnée, 0 maintenue,
    -28 % net) ressortait « couverture élargie » alors qu'il recule : une
    étiquette positive sur un article en baisse envoie le mauvais signal.
    """
    d = _diagnose(_article(net=-28.2, maturity=19, gained=1, lost=2, held=0))
    assert d not in (DIAGS["coverage"], DIAGS["ranking"])
    assert d == DIAGS["narrowed"]


def test_a_mature_decline_is_diagnosed_on_its_queries():
    """Passé le seuil de recul, une chute s'impute bien au contenu."""
    assert _diagnose(
        _article(net=-46.0, maturity=30, gained=5, lost=62, held=6)
    ) == DIAGS["query_loss"]


def test_coverage_beats_ranking_when_the_article_widens():
    """Le cas d'école : volume en forte hausse, position en recul.

    `polariser-lumiere-physique` (+310 % net, position 9,9 → 10,6, 83 requêtes
    gagnées) doit se lire comme un élargissement, pas comme un échec de
    classement. Aucune métrique par page ne pouvait le dire.
    """
    assert _diagnose(
        _article(net=310.5, maturity=30, gained=83, lost=23, held=20)
    ) == DIAGS["coverage"]


def test_diagnosis_is_none_without_query_data():
    """`--no-queries` supprime la collecte : ne rien affirmer plutôt que deviner."""
    assert _diagnose({"maturity": 30, "net_impressions_pct": 50.0,
                      "before": {"impressions": 10},
                      "after": {"impressions": 20}}) is None


# ---------------------------------------------------------------------------
# Affichage
# ---------------------------------------------------------------------------

def test_position_is_displayed_without_decimals():
    """Une position GSC est une moyenne pondérée : on n'est pas « 8,4e »."""
    assert _pos(8.4) == "8"
    assert _pos(7.5) == "8"
    assert _pos(None) == "–"


def test_position_delta_survives_rounding():
    """Arrondir AVANT le delta effacerait le mouvement.

    8,4 → 7,5 est un gain réel de 0,9 place. En arrondissant d'abord, les deux
    valent 8 et la cellule afficherait « +0 » : l'arrondi masquerait ce que la
    colonne existe pour montrer.
    """
    cell = _pos_cell(8.4, 7.5)
    assert "+1" in cell
    assert "+0" not in cell


def test_a_page_starting_from_zero_reports_volume_not_na():
    """Une page invisible avant refresh n'a pas de pourcentage de progression.

    Afficher « n/a » effaçait de vraies réussites : sur août 2026, quatre
    articles créaient 968 impressions et ressortaient tous comme non mesurables.
    """
    cell = _net_cell({
        "net_impressions_pct": None,
        "before": {"impressions": 0},
        "after": {"impressions": 728},
    })
    assert "nouveau" in cell
    assert "728" in cell
    assert "n/a" not in cell


# ---------------------------------------------------------------------------
# Périmètre : la colonne de date de l'onglet
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("04/08/2026", "2026-08-04"),
    ("2026-08-04", "2026-08-04"),
    ("4/8/2026", "2026-08-04"),
    ("", None),
    ("n/a", None),
    ("32/08/2026", None),   # jour impossible : ignorer plutôt que deviner
])
def test_sheet_date_parsing(raw, expected):
    """La colonne est saisie à la main : deux formats coexistent.

    Une valeur non reconnue est ignorée et non devinée — une date fausse
    déplacerait l'article de vague et fausserait sa fenêtre de mesure.
    """
    from scripts.audit.impact_cohort import _parse_fr_date
    assert _parse_fr_date(raw) == expected


def test_a_last_rank_fallback_must_not_widen_the_scope():
    """La leçon du faux d'août 2026, verrouillée dans le code.

    Le rapport annonçait 166 articles là où l'onglet en déclarait 86 : le repli
    sur `modified` (rang 3) ne comblait pas un trou dans un lot connu, il
    *définissait* le lot. Un article refreshé en juin, simplement réédité
    depuis, ressortait comme la plus forte progression du mois.

    En mode `--tab`, la source doit donc être exclusive : aucune date WordPress
    ne doit pouvoir entrer. Même exigence pour `--source notion`, qui est le
    pendant du mode `--tab` sur un site à publication manuelle : le sitemap y
    comble un trou dans un lot connu (les URLs que la base déclare en ligne)
    et ne définit jamais le lot.
    """
    src = MODULE.read_text(encoding="utf-8")
    assert "_pushed_dates_from_sheet_column" in src
    # Le mode --tab court-circuite les autres sources plutôt que de s'y ajouter.
    assert "elif tab:" in src
    assert '"sheet_column" if tab' in src
    # Le complément sitemap est borné aux URLs que la base Notion suit.
    assert "_notion_online_slugs" in src
    assert "if slug in known and slug not in pushed_by_slug" in src


def test_control_excludes_refreshes_outside_the_scope():
    """En mode --tab, le lot mesuré est un sous-ensemble des refreshs du mois.

    Les autres ont bougé eux aussi. Les laisser dans le groupe de contrôle
    ferait passer leur progression pour de la saisonnalité, gonflerait le
    rythme « naturel » du site et sous-estimerait l'écart net du lot.
    """
    src = MODULE.read_text(encoding="utf-8")
    assert "excluded_urls" in src
    assert "u not in excluded_urls" in src


# ---------------------------------------------------------------------------
# Fiche par URL : top requêtes fusionnées et lecture rédigée
# ---------------------------------------------------------------------------

def _q(imp, pos=None, clicks=0):
    return {"impressions": imp, "clicks": clicks, "position": pos}


def test_query_movement_keeps_a_merged_top_ranked_on_either_side():
    """La fiche affiche les requêtes qui pèsent le plus AVANT OU APRÈS.

    Classer sur le seul « après » ferait disparaître la requête perdue à 414
    impressions (le vrai sujet d'un recul) et la requête maintenue qui
    s'effondre (368 → 5), derrière des requêtes gagnées à 1 impression.
    """
    before = {"laser": _q(414, 89.0), "principe": _q(368, 20.0)}
    after = {"principe": _q(5, 30.0), "physique": _q(40, 5.0)}
    after.update({f"g{i}": _q(1, 50.0) for i in range(6)})
    m = _query_movement(before, after, 3)
    assert [x["query"] for x in m["top"]] == ["laser", "principe", "physique"]
    assert [x["kind"] for x in m["top"]] == ["perdue", "maintenue", "gagnée"]
    # les familles restent disponibles à côté, tronquées à n
    assert len(m["gained"]) == 3 and m["counts"]["gained"] == 7


def test_plural_applies_to_every_word():
    assert _pl(5, "requête perdue") == "5 requêtes perdues"
    assert _pl(1, "requête perdue") == "1 requête perdue"
    assert _pl(1, "impression") == "1 impression"


def _card(ib, ia, held=(), gained=(), lost=(), counts=None):
    def rows(items, before, after):
        out = []
        for q, b, a, pb, pa in items:
            out.append({"query": q, "impressions_before": b, "impressions_after": a,
                        "clicks_before": 0, "clicks_after": 0,
                        "position_before": pb, "position_after": pa,
                        **({"position_delta": round(pb - pa, 1)}
                           if pb is not None and pa is not None else {})})
        return out
    h, g, l = rows(held, 1, 1), rows(gained, 0, 1), rows(lost, 1, 0)
    c = counts or {"held": len(h), "gained": len(g), "lost": len(l),
                   "before": len(h) + len(l), "after": len(h) + len(g)}
    return {"before": {"impressions": ib}, "after": {"impressions": ia},
            "queries": {"held": h, "gained": g, "lost": l, "counts": c}}


def test_reading_names_the_real_queries_and_states_no_cause():
    a = _card(907, 45,
                 held=[("comment fonctionne un laser", 23, 2, 80.0, 36.0)],
                 lost=[("laser", 414, 0, 89.0, None), ("le laser", 9, 0, 72.0, None)],
                 gained=[("physique", 0, 1, None, 2.0)])
    txt = _query_reading(a)
    assert "« laser »" in txt and "414 impressions" in txt
    assert "2 requêtes" in txt and "requête perdues" not in txt
    for banned in ("attribuable", "grâce au", "prouve", "démontre"):
        assert banned not in txt
    # 2 → 23 impressions : la position n'est pas citée sur si peu de volume
    assert "gagne 44 places" not in txt


def test_reading_says_when_gsc_attributes_little_of_the_volume():
    """309 impressions sur la page, 6 sur ses requêtes visibles : dire que le
    volume « vient » de ces requêtes serait faux."""
    a = _card(144, 309,
                 gained=[("pythagore", 0, 2, None, 8.0), ("classe", 0, 1, None, 8.0),
                         ("a", 0, 1, None, 9.0), ("b", 0, 1, None, 9.0), ("c", 0, 1, None, 9.0)],
                 lost=[("pythagore exercice", 10, 0, 74.0, None)])
    txt = _query_reading(a)
    assert "n'attribue" in txt and "309" in txt
    assert "part visible" in txt


def test_reading_cites_a_position_move_only_on_volume():
    a = _card(100, 250,
                 held=[("miss marple", 1, 250, 1.0, 3.0),
                       ("qui est miss marple", 3, 25, 26.0, 5.0),
                       ("bruit", 2, 2, 80.0, 22.0)])
    txt = _query_reading(a)
    assert "« qui est miss marple » gagne 21 places" in txt
    assert "58 places" not in txt
