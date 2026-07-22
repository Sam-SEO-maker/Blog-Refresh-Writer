"""Sync Notion « config pays » → catalogue (enrichissement par jointure URL).

Vérifie la SÛRETÉ de l'enrichissement (aucune perte d'entrée, changelog fidèle,
non-appariés signalés) et le parsing des propriétés Notion — sans accès réseau.

NOTE : l'ancienne API `merge_into_sites`/`row_to_site` (merge direct dans
sites.json) a été remplacée par `enrich_catalog`/`row_to_labels` (jointure par
gsc_property) ; ce fichier teste l'API actuelle.
"""

from scripts.notion.sync_sites_from_notion import (
    enrich_catalog,
    row_to_labels,
    _plain_value,
    _norm_url,
)


def _row(pays=None, url=None):
    props = {}
    if pays is not None:
        props["Pays"] = {"type": "rich_text", "rich_text": [{"plain_text": pays}]}
    if url is not None:
        props["URL du blog"] = {"type": "url", "url": url}
    return {"properties": props}


def _catalog():
    return {
        "sites": [
            {"site_slug": "es-es-ressources", "type": "ressources",
             "gsc_property": "https://www.superprof.es/apuntes/"},
            {"site_slug": "fr-fr-blog", "type": "blog",
             "gsc_property": "https://www.superprof.fr/blog/"},
        ],
    }


def test_enrich_applies_labels_and_logs_changes():
    cat, changes, unmatched = enrich_catalog(
        _catalog(), [_row(pays="Espagne", url="https://www.superprof.es/apuntes")])
    entry = next(e for e in cat["sites"] if e["site_slug"] == "es-es-ressources")
    assert entry["country_label"] == "Espagne"
    assert any("es-es-ressources.country_label" in c for c in changes)
    assert unmatched == []


def test_enrich_no_change_returns_empty_changelog():
    cat = _catalog()
    cat["sites"][0]["country_label"] = "Espagne"
    _, changes, _ = enrich_catalog(
        cat, [_row(pays="Espagne", url="https://www.superprof.es/apuntes/")])
    assert changes == []


def test_enrich_reports_unmatched_and_loses_nothing():
    cat, _, unmatched = enrich_catalog(
        _catalog(), [_row(pays="Chili", url="https://www.superprof.cl/blog/")])
    assert len(cat["sites"]) == 2  # aucune entrée créée ni perdue
    assert unmatched and "Chili" in unmatched[0]


def test_row_to_labels_requires_url():
    assert row_to_labels(_row(pays="Espagne")) is None
    labels = row_to_labels(_row(pays="Espagne", url="https://x.fr/blog/"))
    assert labels == {"country_label": "Espagne", "_url": "https://x.fr/blog/"}


def test_norm_url_joins_variants():
    assert _norm_url("https://X.fr/Blog") == _norm_url("https://x.fr/blog/")


def test_plain_value_types():
    assert _plain_value({"type": "url", "url": "https://x.fr"}) == "https://x.fr"
    assert _plain_value({"type": "select", "select": {"name": "low"}}) == "low"
    assert _plain_value({"type": "select", "select": None}) is None
    assert _plain_value(
        {"type": "rich_text", "rich_text": [{"plain_text": "Héllo"}]}
    ) == "Héllo"
    assert _plain_value({"type": "checkbox", "checkbox": True}) is None  # non mappé
