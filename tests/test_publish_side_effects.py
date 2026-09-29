"""Effets de bord d'une publication réussie : statut Sheet et appariement CSV.

Deux régressions constatées en production (lot « Medium Potential » 201-249) :

1. Ni `finalize` ni `push` n'écrivaient le statut dans la Sheet. Les lignes
   restaient « A faire » après publication, et `batch refresh --rows` les
   reproposait : un lot de 10 URLs déjà publiées a été re-préparé de bout en
   bout, consommant 10 guides YTG et 10 audits SERP pour rien.

2. `generate_table_csv` cherchait `{slug}.gutenberg.html` alors que la chaîne
   écrit `{slug}_refreshed.gutenberg.html` : l'outil affichait « ABSENT » sur
   tous les articles du pipeline, et les ZIP devaient être reconstruits à la main.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.sheets import tab_status
from scripts.sheets.tab_status import PUBLISHED_STATUS, StatusUpdate, mark_published
from scripts.utils import generate_table_csv
from scripts.utils.output_lookup import strip_output_suffixes


class TestMarkPublished:
    """`mark_published` pose le statut sans jamais pouvoir casser un push."""

    def test_statut_est_redige_pas_publie(self):
        """Le push met en ligne ; la validation éditoriale reste à faire.

        « Publié » est réservé à l'arbitrage humain : c'est une consigne
        explicite de l'équipe, pas une nuance cosmétique.
        """
        assert PUBLISHED_STATUS == "Rédigé"

    def test_succes_renvoie_onglet_et_ligne(self, monkeypatch):
        monkeypatch.setattr(
            tab_status, "update_status",
            lambda *a, **k: StatusUpdate(tab="Medium Potential", row=229,
                                         written=True, date="21/09/2026"),
        )
        msg = mark_published("superprof.fr-ressources", "https://x/y.html")
        assert "Medium Potential" in msg and "229" in msg and "Rédigé" in msg

    def test_exception_sheet_ne_leve_pas(self, monkeypatch):
        """L'article est DÉJÀ en ligne : une Sheet injoignable ne doit pas
        transformer une publication réussie en échec."""
        def boom(*a, **k):
            raise RuntimeError("credentials unavailable")
        monkeypatch.setattr(tab_status, "update_status", boom)

        msg = mark_published("superprof.fr-ressources", "https://x/y.html")
        assert "not written" in msg and "credentials unavailable" in msg

    def test_url_hors_onglet_ne_leve_pas(self, monkeypatch):
        monkeypatch.setattr(tab_status, "update_status", lambda *a, **k: None)
        msg = mark_published("superprof.fr-ressources", "https://x/absente.html")
        assert "not written" in msg

    def test_onglet_sans_colonne_statut(self, monkeypatch):
        monkeypatch.setattr(
            tab_status, "update_status",
            lambda *a, **k: StatusUpdate(tab="Sans statut", row=12,
                                         written=False, reason="no status column"),
        )
        msg = mark_published("superprof.fr-ressources", "https://x/y.html")
        assert "not written" in msg and "no status column" in msg

    def test_transmet_le_statut_publie(self, monkeypatch):
        """La valeur écrite est bien PUBLISHED_STATUS, pas autre chose."""
        captured = {}

        def spy(site, url, value, tab=None, date=None):
            captured["value"] = value
            return StatusUpdate(tab="T", row=1, written=True, date=None)

        monkeypatch.setattr(tab_status, "update_status", spy)
        mark_published("superprof.fr-ressources", "https://x/y.html")
        assert captured["value"] == PUBLISHED_STATUS


class TestFindGutenberg:
    """Le nom réel produit par la chaîne porte le suffixe `_refreshed`."""

    @pytest.fixture
    def html_dir(self, tmp_path, monkeypatch):
        d = tmp_path / "html"
        (d / "articles_260922").mkdir(parents=True)
        monkeypatch.setattr(generate_table_csv, "HTML", d)
        return d

    def test_trouve_le_nom_du_pipeline(self, html_dir):
        """C'est LE cas qui échouait : le fichier existe, l'outil disait ABSENT."""
        f = html_dir / "articles_260922" / "foyers-de-peuplement_refreshed.gutenberg.html"
        f.write_text("<table></table>", encoding="utf-8")

        found = generate_table_csv.find_gutenberg("foyers-de-peuplement", "articles_260922")
        assert found == f

    def test_trouve_aussi_le_nom_nu(self, html_dir):
        """L'ancienne convention reste acceptée (fichiers historiques)."""
        f = html_dir / "articles_260922" / "vieux-article.gutenberg.html"
        f.write_text("<table></table>", encoding="utf-8")

        assert generate_table_csv.find_gutenberg("vieux-article", "articles_260922") == f

    def test_scan_recursif_hors_dossier_date(self, html_dir):
        """Un article généré un autre jour reste trouvable."""
        f = html_dir / "nerf-ligament-tendon_refreshed.gutenberg.html"
        f.write_text("<table></table>", encoding="utf-8")

        assert generate_table_csv.find_gutenberg("nerf-ligament-tendon", "articles_260922") == f

    def test_refreshed_prioritaire_sur_nu(self, html_dir):
        """Les deux coexistent : la version du pipeline gagne, c'est celle
        que `finalize` tient à jour."""
        nu = html_dir / "articles_260922" / "doublon.gutenberg.html"
        refreshed = html_dir / "articles_260922" / "doublon_refreshed.gutenberg.html"
        nu.write_text("<table></table>", encoding="utf-8")
        refreshed.write_text("<table></table>", encoding="utf-8")

        assert generate_table_csv.find_gutenberg("doublon", "articles_260922") == refreshed

    def test_absent_renvoie_none(self, html_dir):
        assert generate_table_csv.find_gutenberg("jamais-ecrit", "articles_260922") is None

    def test_slug_csv_sans_suffixe_refreshed(self):
        """Sans ce strip, les CSV s'appelaient `{slug}_refreshed_tableau_...`."""
        assert strip_output_suffixes(
            "foyers-de-peuplement_refreshed.gutenberg.html") == "foyers-de-peuplement"


class TestCsvNamingConvention:
    """Les deux extracteurs doivent produire LE MÊME nom pour le même tableau.

    Convention projet (mémoire `csv-tableaux-nommage-par-slug`) :
    `{slug}_tableau_{descriptif}.csv`, où le descriptif résume le SUJET du
    tableau. Le nommage par en-têtes de colonnes est « l'ancienne convention
    abandonnée ».

    Deux implémentations divergentes coexistaient : la chaîne nommait par
    en-têtes et indexait dans `_index.csv`, l'outil batch nommait par titre et
    écrivait dans un dossier daté hors index. Six CSV byte-identiques sous des
    noms concurrents sur un seul lot, dont un hors du ZIP livré.
    """

    HTML = (
        "<h1>Article</h1>"
        "<h2>Le poids écrasant de l'Asie 🌏</h2>"
        "<p>Texte.</p>"
        "<table><tr><th>Continent</th><th>Population</th></tr>"
        "<tr><td>Asie</td><td>4835</td></tr></table>"
    )

    def test_descriptif_vient_du_titre_pas_des_entetes(self, tmp_path):
        from scripts.utils.table_csv_extractor import extract_tables_to_csv

        made = extract_tables_to_csv(html_content=self.HTML, csv_dir=tmp_path,
                                     file_slug="foyers-de-peuplement")
        name = made[0].name
        assert name == "foyers-de-peuplement_tableau_poids-ecrasant-asie.csv", name
        # L'ancienne convention (en-têtes) ne doit plus apparaître.
        assert "continent" not in name and "population" not in name

    def test_emoji_et_mots_vides_retires(self, tmp_path):
        from scripts.utils.table_csv_extractor import extract_tables_to_csv

        made = extract_tables_to_csv(html_content=self.HTML, csv_dir=tmp_path,
                                     file_slug="x")
        assert "🌏" not in made[0].name
        for stop in ("-le-", "-de-", "-l-"):
            assert stop not in made[0].name

    def test_repli_sur_entetes_sans_titre(self, tmp_path):
        """Sans titre avant le tableau, les en-têtes valent mieux qu'un
        `table_1` anonyme."""
        from scripts.utils.table_csv_extractor import extract_tables_to_csv

        html = "<table><tr><th>Terme</th><th>Sens</th></tr><tr><td>a</td><td>b</td></tr></table>"
        made = extract_tables_to_csv(html_content=html, csv_dir=tmp_path, file_slug="art")
        assert made[0].name == "art_tableau_terme_sens.csv"

    def test_les_deux_outils_donnent_le_meme_nom(self, tmp_path, monkeypatch):
        """Le test qui aurait empêché les doublons du lot 201-249."""
        from scripts.utils.table_csv_extractor import extract_tables_to_csv
        from scripts.utils import generate_table_csv as batch_tool

        chaine = tmp_path / "chaine"
        noms_chaine = [p.name for p in extract_tables_to_csv(
            html_content=self.HTML, csv_dir=chaine, file_slug="art")]

        monkeypatch.setattr(batch_tool, "CSVDIR", tmp_path / "batch")
        monkeypatch.setattr(batch_tool, "ZIPDIR", tmp_path / "zips")
        noms_batch = [p.name for p in batch_tool.gen_for("art", self.HTML)]

        assert noms_chaine == noms_batch

    def test_outil_batch_ecrit_a_plat_et_indexe(self, tmp_path, monkeypatch):
        """Pas de sous-dossier daté : `_index.csv` référence le dossier plat."""
        from scripts.utils import generate_table_csv as batch_tool

        csv_dir, zip_dir = tmp_path / "csv", tmp_path / "zips"
        monkeypatch.setattr(batch_tool, "CSVDIR", csv_dir)
        monkeypatch.setattr(batch_tool, "ZIPDIR", zip_dir)

        made = batch_tool.gen_for("art", self.HTML)
        assert made[0].parent == csv_dir, "CSV écrit hors du dossier plat indexé"
        assert (csv_dir / "_index.csv").exists(), "_index.csv non maintenu"
        assert (zip_dir / "art_tableaux.zip").exists()

    def test_zip_contient_exactement_les_csv_generes(self, tmp_path, monkeypatch):
        """Le ZIP livré et les CSV sur disque ne doivent pas diverger."""
        import zipfile
        from scripts.utils import generate_table_csv as batch_tool

        monkeypatch.setattr(batch_tool, "CSVDIR", tmp_path / "csv")
        monkeypatch.setattr(batch_tool, "ZIPDIR", tmp_path / "zips")

        made = batch_tool.gen_for("art", self.HTML)
        with zipfile.ZipFile(tmp_path / "zips" / "art_tableaux.zip") as z:
            assert sorted(z.namelist()) == sorted(p.name for p in made)


class TestFindZip:
    """Localiser le ZIP de tableaux d'un article.

    Le balayage n'est pas cosmétique : les ZIP des fournées passées vivent dans
    des sous-dossiers datés et dans `_archive/`, parfois préfixés du nom de lot.
    Ne regarder qu'à la racine a fait compter 47 articles couverts là où le
    balayage complet en trouvait 92.
    """

    def _make(self, root: Path, rel: str) -> Path:
        p = root / "csv_zips" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"PK\x03\x04")
        return p

    def test_racine_prioritaire(self, tmp_path):
        from scripts.notion.zip_attachment import find_zip

        self._make(tmp_path, "articles_260909/art_tableaux.zip")
        racine = self._make(tmp_path, "art_tableaux.zip")
        assert find_zip(tmp_path, "art") == racine

    def test_trouve_dans_sous_dossier_date(self, tmp_path):
        from scripts.notion.zip_attachment import find_zip

        cible = self._make(tmp_path, "articles_260909/art_tableaux.zip")
        assert find_zip(tmp_path, "art") == cible

    def test_trouve_nom_prefixe_du_lot(self, tmp_path):
        from scripts.notion.zip_attachment import find_zip

        cible = self._make(tmp_path, "_archive/p/articles_260903__art_tableaux.zip")
        assert find_zip(tmp_path, "art") == cible

    def test_ne_confond_pas_deux_slugs_voisins(self, tmp_path):
        """`art` ne doit pas ramasser le ZIP de `autre-art`."""
        from scripts.notion.zip_attachment import find_zip

        self._make(tmp_path, "articles_260909/autre-art_tableaux.zip")
        assert find_zip(tmp_path, "art") is None

    def test_absent_rend_none(self, tmp_path):
        from scripts.notion.zip_attachment import find_zip

        (tmp_path / "csv_zips").mkdir()
        assert find_zip(tmp_path, "art") is None


class TestSlugFromUrl:
    def test_retire_extension_html(self):
        from scripts.notion.zip_attachment import slug_from_url

        url = "https://www.superprof.fr/ressources/svt/svt-2nde/nature-du-vivant.html"
        assert slug_from_url(url) == "nature-du-vivant"

    def test_supporte_url_sans_extension(self):
        from scripts.notion.zip_attachment import slug_from_url

        assert slug_from_url("https://x.fr/a/b/mon-article/") == "mon-article"


class TestAttachTablesZipMessage:
    """Contrat d'appel depuis la livraison : ne JAMAIS faire échouer un push.

    L'article est déjà en ligne quand cette fonction s'exécute. Une base Notion
    injoignable ou un token absent ne doivent pas transformer une publication
    réussie en échec — même contrat que `mark_published`.
    """

    def test_exception_ne_leve_pas(self, monkeypatch):
        from scripts.notion import zip_attachment

        def boom(*a, **k):
            raise RuntimeError("réseau")

        monkeypatch.setattr(zip_attachment, "attach_tables_zip", boom)
        msg = zip_attachment.attach_tables_zip_message("site", "https://x.fr/a.html")
        assert msg and "RuntimeError" in msg

    def test_pas_de_zip_reste_muet(self, monkeypatch):
        """Un article sans tableau n'a pas de ZIP : ce n'est pas une anomalie."""
        from scripts.notion import zip_attachment

        monkeypatch.setattr(
            zip_attachment, "attach_tables_zip",
            lambda *a, **k: {"ok": False, "reason": "no_zip", "zip": None},
        )
        assert zip_attachment.attach_tables_zip_message("s", "https://x.fr/a.html") is None

    def test_site_sans_base_notion_reste_muet(self, monkeypatch):
        from scripts.notion import zip_attachment

        monkeypatch.setattr(
            zip_attachment, "attach_tables_zip",
            lambda *a, **k: {"ok": False, "reason": "no_config", "zip": None},
        )
        assert zip_attachment.attach_tables_zip_message("s", "https://x.fr/a.html") is None

    def test_succes_nomme_le_fichier(self, monkeypatch):
        from scripts.notion import zip_attachment

        monkeypatch.setattr(
            zip_attachment, "attach_tables_zip",
            lambda *a, **k: {"ok": True, "reason": "attached",
                             "zip": "/out/csv_zips/art_tableaux.zip"},
        )
        msg = zip_attachment.attach_tables_zip_message("s", "https://x.fr/a.html")
        assert "art_tableaux.zip" in msg

    def test_echec_est_signale(self, monkeypatch):
        """Un token absent doit se voir : silencieux, le câblage serait mort."""
        from scripts.notion import zip_attachment

        monkeypatch.setattr(
            zip_attachment, "attach_tables_zip",
            lambda *a, **k: {"ok": False, "reason": "no_token", "zip": None},
        )
        msg = zip_attachment.attach_tables_zip_message("s", "https://x.fr/a.html")
        assert msg and "NOTION_TOKEN" in msg


class TestPasDeDoublon:
    """`insert`/`append` ne déduplique pas côté Notion : c'est à nous de le faire.

    Constaté en production : un lot de 15 pages a produit 2 doublons, la page
    portant deux fois le même ZIP sous deux `attachment` distincts. L'accusé de
    réception de l'API ne dit pas combien de blocs existent.
    """

    class _FakeClient:
        API_BASE_URL = "https://api.notion.com/v1"
        API_VERSION = "2022-06-28"
        is_configured = True
        _token = "t"

        def __init__(self, pages):
            self._pages = pages

        def _headers(self):
            return {}

        def query_database(self, database_id):
            return self._pages

    @pytest.fixture
    def site(self, tmp_path, monkeypatch):
        """Un site minimal : config avec base Notion + un ZIP sur disque."""
        cfg_dir = tmp_path / "sites" / "s" / "config"
        cfg_dir.mkdir(parents=True)
        (cfg_dir / "site.json").write_text(
            '{"notion": {"orders": {"database_id": "db",'
            ' "col_url": "Local resource URL"}}}', encoding="utf-8")
        out = tmp_path / "sites" / "s" / "outputs"
        (out / "csv_zips").mkdir(parents=True)
        (out / "csv_zips" / "art_tableaux.zip").write_bytes(b"PK\x03\x04")

        from scripts.notion import zip_attachment

        class _Paths:
            def __init__(self, base_path=None):
                pass

            def site_config(self, site):
                return cfg_dir / "site.json"

            def output_dir(self, site):
                return out

        import _shared.core.site_paths as sp
        monkeypatch.setattr(sp, "SitePaths", _Paths)
        return zip_attachment

    def _row(self, url):
        return {"id": "page1", "properties": {
            "Local resource URL": {"type": "url", "url": url}}}

    def test_zip_deja_present_nattache_rien(self, site, monkeypatch):
        import scripts.notion as notion_pkg

        client = self._FakeClient([self._row("https://x.fr/a/art.html")])
        monkeypatch.setattr(notion_pkg, "NotionClient", lambda: client)
        monkeypatch.setattr(site, "_page_file_names", lambda c, p: ["art_tableaux.zip"])

        def jamais(*a, **k):
            raise AssertionError("upload lancé alors que le ZIP est déjà là")

        monkeypatch.setattr(site, "_upload_file", jamais)
        res = site.attach_tables_zip("s", "https://x.fr/a/art.html")
        assert res["ok"] and res["reason"] == "already"

    def test_page_illisible_nattache_pas(self, site, monkeypatch):
        """Ne pas pouvoir lire n'est pas « il n'y a rien » : on s'abstient."""
        import scripts.notion as notion_pkg

        client = self._FakeClient([self._row("https://x.fr/a/art.html")])
        monkeypatch.setattr(notion_pkg, "NotionClient", lambda: client)
        monkeypatch.setattr(site, "_page_file_names", lambda c, p: None)

        def jamais(*a, **k):
            raise AssertionError("upload lancé sur un état de page inconnu")

        monkeypatch.setattr(site, "_upload_file", jamais)
        res = site.attach_tables_zip("s", "https://x.fr/a/art.html")
        assert not res["ok"] and res["reason"] == "unreadable"

    def test_page_vide_attache(self, site, monkeypatch):
        import scripts.notion as notion_pkg

        client = self._FakeClient([self._row("https://x.fr/a/art.html")])
        monkeypatch.setattr(notion_pkg, "NotionClient", lambda: client)
        monkeypatch.setattr(site, "_page_file_names", lambda c, p: [])
        monkeypatch.setattr(site, "_upload_file", lambda c, z: "up1")
        monkeypatch.setattr(site, "_append_file_block", lambda c, p, u, n: True)

        res = site.attach_tables_zip("s", "https://x.fr/a/art.html")
        assert res["ok"] and res["reason"] == "attached"

    def test_url_absente_de_la_base(self, site, monkeypatch):
        import scripts.notion as notion_pkg

        client = self._FakeClient([self._row("https://x.fr/a/autre.html")])
        monkeypatch.setattr(notion_pkg, "NotionClient", lambda: client)
        res = site.attach_tables_zip("s", "https://x.fr/a/art.html")
        assert not res["ok"] and res["reason"] == "no_row"

    def test_appariement_insensible_au_www_et_au_slash(self, site, monkeypatch):
        """La Sheet et Notion ne notent pas les URLs de la même façon."""
        import scripts.notion as notion_pkg

        client = self._FakeClient([self._row("http://x.fr/a/art.html")])
        monkeypatch.setattr(notion_pkg, "NotionClient", lambda: client)
        monkeypatch.setattr(site, "_page_file_names", lambda c, p: [])
        monkeypatch.setattr(site, "_upload_file", lambda c, z: "up1")
        monkeypatch.setattr(site, "_append_file_block", lambda c, p, u, n: True)

        res = site.attach_tables_zip("s", "https://www.x.fr/a/art.html")
        assert res["ok"], "URL équivalente non appariée"

    def test_base_inaccessible_nest_pas_une_ligne_manquante(self, site, monkeypatch):
        """404 d'accès et URL absente sont deux problèmes, deux messages.

        `query_database` avale le 404 et rend []. Confondre les deux envoie
        chercher une ligne dans une base qu'on ne peut pas lire.
        """
        import scripts.notion as notion_pkg

        client = self._FakeClient([])  # ni ligne, ni accès : indiscernable ici
        monkeypatch.setattr(notion_pkg, "NotionClient", lambda: client)
        res = site.attach_tables_zip("s", "https://x.fr/a/art.html")
        assert res["reason"] == "no_access"

        msg = site.attach_tables_zip_message("s", "https://x.fr/a/art.html")
        assert "share it with the integration" in msg
