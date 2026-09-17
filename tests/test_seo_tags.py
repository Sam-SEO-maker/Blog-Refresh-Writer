"""Tests pour la génération des balises SEO via l'outil du backoffice WP.

Deux familles de cas, toutes deux tirées du parc réel (onglet Medium Potential,
563 lignes « A faire ») :

- la **cascade** imposée par le plugin (title → h1 → meta), et le mot-clé
  propre à chaque étape (main en colonne B pour le title, secondary en
  colonne C pour le H1) ;
- le **filtre de conformité**, qui doit attraper les fautes que le générateur
  recopie du mot-clé sans rejeter les variantes légitimes. C'est la
  distinction la plus fragile du module : la première version rejetait les
  deux.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.seo.seo_tags import (
    STEP_H1,
    STEP_META,
    STEP_TITLE,
    RowResult,
    Suggestion,
    _choose,
    _violations,
    generate_row,
    read_rows,
)


class _FakeGenerator:
    """Générateur en dur : enregistre les appels, renvoie des propositions fixées."""

    def __init__(self, responses: dict[str, list[str]], errors: dict[str, str] | None = None):
        self.responses = responses
        self.errors = errors or {}
        self.calls: list[dict] = []

    def generate(self, step, keyword, post_id=None, title=None, h1=None, max_attempts=3):
        self.calls.append({"step": step, "keyword": keyword, "title": title, "h1": h1})
        sug = Suggestion(step=step, keyword=keyword)
        # Une étape peut échouer deux fois de suite (le H1 rejoué sur le main KW) :
        # on consomme la liste pour distinguer le premier appel du second.
        key = f"{step}:{keyword}"
        if key in self.errors:
            sug.error = self.errors[key]
            return sug
        sug.options = list(self.responses.get(key, self.responses.get(step, [])))
        return sug


class TestCascade:
    """L'ordre des appels et le mot-clé de chaque étape."""

    def test_chaque_etape_recoit_son_mot_cle(self):
        """Title sur le main KW (colonne B), H1 sur le secondary (colonne C)."""
        gen = _FakeGenerator({
            STEP_TITLE: ["Les piles : bien les choisir en 2026"],
            STEP_H1: ["Choisir ses piles : le guide pratique du quotidien"],
            STEP_META: ["Comparez les piles alcalines, lithium et rechargeables "
                        "pour bien choisir selon vos appareils et vos usages."],
        })
        steps = generate_row(gen, "les piles", "piles rechargeables")

        assert gen.calls[0]["step"] == STEP_TITLE
        assert gen.calls[0]["keyword"] == "les piles"
        assert gen.calls[1]["step"] == STEP_H1
        assert gen.calls[1]["keyword"] == "piles rechargeables"
        assert gen.calls[2]["step"] == STEP_META
        assert all(steps[s].chosen for s in (STEP_TITLE, STEP_H1, STEP_META))

    def test_les_etapes_aval_recoivent_les_valeurs_retenues(self):
        """Le plugin exige title pour le h1, title+h1 pour la meta."""
        gen = _FakeGenerator({
            STEP_TITLE: ["Les piles : bien les choisir en 2026"],
            STEP_H1: ["Choisir ses piles : le guide pratique du quotidien"],
            STEP_META: ["Comparez les piles alcalines, lithium et rechargeables "
                        "pour bien choisir selon vos appareils et vos usages."],
        })
        generate_row(gen, "les piles", "piles rechargeables")

        assert gen.calls[1]["title"] == "Les piles : bien les choisir en 2026"
        assert gen.calls[2]["title"] == "Les piles : bien les choisir en 2026"
        assert gen.calls[2]["h1"] == "Choisir ses piles : le guide pratique du quotidien"

    def test_un_title_manquant_arrete_la_cascade(self):
        """Sans title, le plugin refuse les deux étapes suivantes (sp_missing_title)."""
        gen = _FakeGenerator({}, errors={f"{STEP_TITLE}:les piles": "HTTP 500"})
        steps = generate_row(gen, "les piles", "piles rechargeables")

        assert steps[STEP_TITLE].error == "HTTP 500"
        assert STEP_H1 not in steps and STEP_META not in steps
        assert len(gen.calls) == 1, "aucun appel aval ne doit être tenté"

    def test_secondary_absent_arrete_avant_le_h1(self):
        """Le H1 n'a pas d'entrée sans mot-clé secondaire : la meta suit."""
        gen = _FakeGenerator({STEP_TITLE: ["Les piles : bien les choisir en 2026"]})
        steps = generate_row(gen, "les piles", "")

        assert steps[STEP_TITLE].chosen
        assert steps[STEP_H1].chosen is None
        assert "colonne C" in steps[STEP_H1].error
        assert STEP_META not in steps


class TestConformite:
    """Le filtre des propositions — le cœur fragile du module."""

    def test_tiret_cadratin_rejete(self):
        """Interdit dans tout contenu généré (règle projet)."""
        bad = "Les piles — guide complet pour bien choisir"
        assert "tiret cadratin" in ", ".join(_violations(bad, "les piles", STEP_TITLE))

    def test_abreviation_def_rejetee_dans_un_h1(self):
        """« Enlèvement def » est un titre visible, pas une requête."""
        v = _violations("Enlèvement def : explication simple et exemples",
                        "enlèvement def", STEP_H1)
        assert any("abréviation" in x for x in v)

    def test_singulier_apres_determinant_pluriel_rejete(self):
        """Cas réel ligne 161 : secondary « les pile » vs main « les piles »."""
        v = _violations("Les pile : quels types choisir selon vos usages",
                        "les pile", STEP_H1, reference_keyword="les piles")
        assert any("forme fautive" in x for x in v)

    def test_variante_singuliere_legitime_acceptee(self):
        """Cas réel ligne 169 : « question en anglais » n'est pas une faute.

        Faux positif de la première version du filtre : elle comparait le
        nombre des mots-clés sans regarder le déterminant, et rejetait les 5
        propositions d'un H1 parfaitement correct.
        """
        v = _violations("Question en anglais : 10 idées pour engager la conversation",
                        "question en anglais", STEP_H1,
                        reference_keyword="10 questions à poser en anglais")
        assert v == [], f"ne doit rien reprocher, or : {v}"

    def test_longueur_par_etape(self):
        """Chaque balise a sa limite ; la meta est la plus longue."""
        assert _violations("x" * 200, "kw test", STEP_TITLE)
        assert _violations("x" * 200, "kw test", STEP_META)
        assert _violations("court", "kw test", STEP_TITLE)

    def test_choose_retient_la_premiere_conforme(self):
        """L'ordre du plugin est sa préférence : on la respecte."""
        options = [
            "Les piles — choisir sans se tromper",          # cadratin
            "Les piles : choisir sans se tromper en 2026",   # conforme
            "Les piles : autre proposition correcte ici",
        ]
        chosen, rejected = _choose(options, "les piles", STEP_TITLE)
        assert chosen == "Les piles : choisir sans se tromper en 2026"
        assert len(rejected) == 1 and "cadratin" in rejected[0][1]

    def test_choose_sans_option_conforme(self):
        chosen, rejected = _choose(["Les piles — a", "Les piles – b"],
                                   "les piles", STEP_TITLE)
        assert chosen is None
        assert len(rejected) == 2


class TestFallbackH1:
    """Le rattrapage quand le secondary KW contamine les 5 propositions."""

    def test_h1_rejoue_sur_le_main_kw(self):
        """Un secondary fautif ne doit pas priver l'article de H1 ni de meta."""
        gen = _FakeGenerator({
            STEP_TITLE: ["Enlèvement définition : guide clair pour comprendre"],
            f"{STEP_H1}:enlèvement def": [
                "Enlèvement def : explication simple et exemples",
                "Comment comprendre enlèvement def au quotidien ?",
            ],
            f"{STEP_H1}:enlèvement définition": [
                "Enlèvement définition : ce que recouvre vraiment ce terme",
            ],
            STEP_META: ["Comprendre la définition d'un enlèvement, ses formes et "
                        "le cadre légal en France, avec des exemples concrets."],
        })
        steps = generate_row(gen, "enlèvement définition", "enlèvement def")

        h1 = steps[STEP_H1]
        assert h1.chosen == "Enlèvement définition : ce que recouvre vraiment ce terme"
        assert h1.fallback_from == "enlèvement def", "la substitution doit être traçable"
        # Les rejets du premier essai sont conservés pour la relecture.
        assert any("abréviation" in why for _, why in h1.rejected)
        # La cascade continue : la meta est bien générée.
        assert steps[STEP_META].chosen

    def test_pas_de_fallback_si_le_h1_est_conforme(self):
        gen = _FakeGenerator({
            STEP_TITLE: ["Les piles : bien les choisir en 2026"],
            STEP_H1: ["Choisir ses piles : le guide pratique du quotidien"],
            STEP_META: ["Comparez les piles alcalines, lithium et rechargeables "
                        "pour bien choisir selon vos appareils et vos usages."],
        })
        steps = generate_row(gen, "les piles", "piles rechargeables")
        assert steps[STEP_H1].fallback_from is None
        assert sum(1 for c in gen.calls if c["step"] == STEP_H1) == 1


class _FakeSheets:
    def __init__(self, rows):
        self._rows = rows
        self.updates = None

    def _read_sheet(self, name):
        return self._rows

    def _batch_update_cells(self, updates):
        self.updates = updates
        return True


class TestLectureOnglet:
    """Le layout vient du config, jamais d'une supposition."""

    TAB = {"col_url": 0, "col_keyword": 1, "col_keyword_secondary": 2,
           "col_title": 5, "col_h1": 6, "col_metadesc": 7, "col_status": 8}

    def _rows(self):
        return [
            ["URL", "Main Keyword", "Secondary Keywords", "Third", "Date",
             "Title", "H1", "Metadescription", "Statut"],
            ["https://x.fr/a.html", "les piles", "piles rechargeables", "", "",
             "", "", "", "A faire"],
            ["https://x.fr/b.html", "deja fait", "sec", "", "",
             "Titre posé à la main", "H1 posé", "Meta posée", "A faire"],
            ["https://x.fr/c.html", "publie", "sec", "", "", "", "", "", "Publié"],
        ]

    def test_numerotation_conforme_a_google_sheets(self):
        """Les numéros de ligne doivent être ceux que Sheets affiche."""
        rows = read_rows(_FakeSheets(self._rows()), self.TAB, "T", {"a faire"})
        assert [r.row for r in rows] == [2]

    def test_statut_en_liste_blanche(self):
        """Seul « à faire » est traité : « Publié » ne doit jamais repasser."""
        urls = [r.url for r in read_rows(_FakeSheets(self._rows()), self.TAB, "T", {"a faire"})]
        assert "https://x.fr/c.html" not in urls

    def test_les_balises_deja_posees_sont_preservees(self):
        """Un choix humain ne s'écrase pas sans --all-rows."""
        default = [r.url for r in read_rows(_FakeSheets(self._rows()), self.TAB, "T", {"a faire"})]
        assert "https://x.fr/b.html" not in default

        forced = [r.url for r in read_rows(_FakeSheets(self._rows()), self.TAB, "T",
                                           {"a faire"}, only_missing=False)]
        assert "https://x.fr/b.html" in forced

    def test_ecriture_dans_les_colonnes_declarees(self):
        from scripts.seo.seo_tags import write_sheet

        r = RowResult(url="https://x.fr/a.html", row=2)
        r.steps = {
            STEP_TITLE: Suggestion(STEP_TITLE, "kw", chosen="Un titre"),
            STEP_H1: Suggestion(STEP_H1, "kw", chosen="Un H1"),
            STEP_META: Suggestion(STEP_META, "kw", chosen="Une meta"),
        }
        client = _FakeSheets([])
        n = write_sheet(client, self.TAB, "T", [r])

        assert n == 3
        cells = {u["cell"]: u["value"] for u in client.updates}
        assert cells == {"F2": "Un titre", "G2": "Un H1", "H2": "Une meta"}

    def test_onglet_sans_colonnes_de_sortie_refuse(self):
        """« New Growing List » n'a pas ces colonnes : écrire en F/G/H y
        écraserait « Impressions 12 mois »."""
        from scripts.seo.seo_tags import write_sheet

        r = RowResult(url="https://x.fr/a.html", row=2)
        r.steps = {STEP_TITLE: Suggestion(STEP_TITLE, "kw", chosen="Un titre")}
        with pytest.raises(ValueError, match="ne déclare pas où écrire"):
            write_sheet(_FakeSheets([]), {"col_url": 0, "col_keyword": 1}, "NGL", [r])
