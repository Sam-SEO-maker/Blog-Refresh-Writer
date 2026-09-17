"""Génère title / H1 / meta description via l'outil IA du backoffice WP.

Remplace le parcours manuel « copier le KW depuis la Sheet → coller dans
l'outil WP → generate → choisir → enregistrer », répété trois fois par article.

L'outil du backoffice est exposé en REST par le plugin maison *Scripts
Superprof* : `POST /wp-json/sp/v1/generate-seo-content`, avec
`type` ∈ {title, h1, meta-description}. Il renvoie 5 propositions, comme
l'écran d'admin — ce module les collecte, en retient une et écrit le tout
dans la Sheet.

Trois contraintes découvertes en sondant l'API, qui dictent la forme du code :

1. **Les trois appels sont une cascade, pas trois appels indépendants.**
   `h1` exige le meta title (sinon `sp_missing_title`), et `meta-description`
   exige title *et* h1 (sinon `sp_missing_h1`). L'ordre est donc imposé, et un
   échec sur le title condamne les deux étapes suivantes de la ligne.

2. **Chaque étape a son propre mot-clé.** Le title se génère sur le *main*
   keyword (colonne B), le H1 sur le *secondary* (colonne C). C'est la règle
   du flux manuel : la reproduire est ce qui rend la sortie comparable à ce
   que produit le backoffice. Une ligne sans secondary KW ne peut pas passer
   l'étape H1, donc pas la meta description non plus.

3. **Le plugin ne sauvegarde rien.** Ses réponses d'erreur le disent
   elles-mêmes (« the post was NOT saved »). Générer est sans effet de bord :
   seul `--write-sheet` (Sheet) ou `--push-wp` (SEOPress) écrit quoi que ce
   soit. C'est ce qui permet un dry-run franc, sans « au cas où ».

Le layout de l'onglet est lu depuis `sheets.tabs` du site.json, jamais supposé :
« Medium Potential » porte les colonnes Title/H1/Metadescription en F/G/H, et
« New Growing List » ne les a pas du tout.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import requests

from _shared.core.site_paths import SitePaths

logger = logging.getLogger(__name__)

# Les trois étapes, dans l'ordre que la cascade impose, chacune avec la
# colonne de mot-clé qui l'alimente et la colonne de sortie qu'elle remplit.
STEP_TITLE = "title"
STEP_H1 = "h1"
STEP_META = "meta-description"
STEPS = (STEP_TITLE, STEP_H1, STEP_META)

# Clés SEOPress : le plugin SEO du site (vérifié sur le parc, ce sont les
# seules meta exposées en REST pour le titre et la description).
SEOPRESS_TITLE = "_seopress_titles_title"
SEOPRESS_DESC = "_seopress_titles_desc"

# Le H1 n'est pas une meta SEO : côté Superprof Ressources c'est le premier
# bloc Gutenberg du corps. Il n'est donc jamais poussé en meta — il reste dans
# la Sheet pour la relecture, et c'est le refresh qui le porte dans le contenu.
_PUSHABLE = {STEP_TITLE: SEOPRESS_TITLE, STEP_META: SEOPRESS_DESC}


@dataclass
class Suggestion:
    """Les propositions d'une étape, et celle retenue."""

    step: str
    keyword: str
    options: list[str] = field(default_factory=list)
    chosen: Optional[str] = None
    rejected: list[tuple[str, str]] = field(default_factory=list)
    error: Optional[str] = None
    # Renseigné quand l'étape a dû être rejouée sur un autre mot-clé (H1 dont
    # le secondary KW était fautif) : la relecture doit voir la substitution.
    fallback_from: Optional[str] = None


@dataclass
class RowResult:
    """Ce qu'une ligne de la Sheet a produit, étape par étape."""

    url: str
    row: int
    main_keyword: str = ""
    secondary_keyword: str = ""
    steps: dict[str, Suggestion] = field(default_factory=dict)
    skipped: Optional[str] = None

    @property
    def ok(self) -> bool:
        return all(self.steps.get(s) and self.steps[s].chosen for s in STEPS)

    def value(self, step: str) -> str:
        s = self.steps.get(step)
        return s.chosen if s and s.chosen else ""


# ---------------------------------------------------------------------------
# Conformité des propositions aux règles éditoriales du repo
# ---------------------------------------------------------------------------

def _agreement_error(text: str, keyword: str, reference: str) -> Optional[str]:
    """Le texte reprend-il une forme fautive du mot-clé, corrigée ailleurs ?

    Cas réel : main KW « les piles », secondary KW « les pile ». Le générateur
    recopie le secondary verbatim et produit « Comment choisir les pile ».

    Le test porte sur l'**accord**, pas sur le nombre : un singulier n'est
    fautif que derrière un déterminant pluriel. « question en anglais » face à
    « 10 questions à poser en anglais » est une variante légitime et doit
    passer ; « les pile » face à « les piles » est une faute. Comparer les
    deux mots-clés sans regarder le déterminant rejetait les deux.
    """
    if not reference:
        return None
    ref_words = set(re.findall(r"\b[\wÀ-ÿ']+\b", reference.lower()))
    low = text.lower()
    plural_det = r"(?:les|des|ces|mes|tes|ses|nos|vos|leurs|plusieurs|quelques|certains|certaines)"
    for m in re.finditer(rf"\b{plural_det}\s+([\wÀ-ÿ']+)\b", low):
        word = m.group(1)
        if len(word) < 4 or word.endswith(("s", "x")):
            continue
        # Un déterminant pluriel suivi d'un singulier : faute confirmée si le
        # mot-clé de référence porte bien le pluriel de ce mot.
        if f"{word}s" in ref_words:
            return f"forme fautive « {m.group(0)} » (le KW principal écrit « {word}s »)"
    return None


def _violations(text: str, keyword: str, step: str,
                reference_keyword: str = "") -> list[str]:
    """Pourquoi cette proposition est inacceptable — liste vide = conforme.

    Le générateur du plugin ignore les règles du repo : il produit des tirets
    cadratins (interdits dans tout contenu généré) et recopie le mot-clé dans
    la casse brute de la Sheet, ce qui donne « Quels sont les ali » sur un
    sigle. Filtrer ici évite de republier à la main ce qu'on vient
    d'automatiser.
    """
    out = []
    if "—" in text or "–" in text:
        out.append("tiret cadratin")

    # Une requête entière recopiée verbatim se lit comme une requête, pas comme
    # un titre : « 8 montages pour quels sont les ALI en TP » vient de là. On
    # signale le cas des mots-clés interrogatifs, qui sont ceux que le plugin
    # insère le plus mal.
    kw = keyword.strip().lower()
    if kw and re.match(r"^(quel|quels|quelle|quelles|comment|pourquoi|est-ce|c'est quoi|qu'est)", kw):
        if kw in text.lower() and not text.lower().startswith(kw):
            out.append("requête interrogative insérée en milieu de phrase")

    # Le H1 est du texte visible par le lecteur, pas une meta : une abréviation
    # de requête (« enlèvement def ») ou une faute recopiée du mot-clé
    # (« les pile ») y est un défaut de publication, alors qu'elle passerait
    # inaperçue dans une balise. Sur le parc Medium Potential, 123 des 563
    # lignes à faire ont un secondary KW qui n'est qu'une variante du main, et
    # 5 contiennent « def » : le générateur les reprend verbatim.
    if step == STEP_H1:
        if re.search(r"\b(def|defi|dfn|abrev)\b", text.lower()):
            out.append("abréviation de requête dans un titre visible")
        if re.search(r"\b(\w+)\s+\1\b", text.lower()):
            out.append("répétition de mot")
        agreement = _agreement_error(text, keyword, reference_keyword)
        if agreement:
            out.append(agreement)

    limits = {STEP_TITLE: 70, STEP_H1: 90, STEP_META: 165}
    if len(text) > limits[step]:
        out.append(f"{len(text)} caractères > {limits[step]}")
    if len(text) < 15:
        out.append("trop court")
    return out


def _choose(options: list[str], keyword: str, step: str,
            reference_keyword: str = "") -> tuple[Optional[str], list[tuple[str, str]]]:
    """Retient la première proposition conforme, et journalise les écarts.

    L'ordre du plugin n'est pas aléatoire : sa première proposition est sa
    préférée. On la garde donc si elle est conforme, plutôt que d'inventer un
    score maison qui divergerait de ce que tu choisis à l'écran.
    """
    rejected: list[tuple[str, str]] = []
    for opt in options:
        opt = (opt or "").strip()
        if not opt:
            continue
        bad = _violations(opt, keyword, step, reference_keyword)
        if not bad:
            return opt, rejected
        rejected.append((opt, ", ".join(bad)))
    return None, rejected


# ---------------------------------------------------------------------------
# Appel du générateur WP
# ---------------------------------------------------------------------------

class SeoTagGenerator:
    """Client de `POST /wp-json/sp/v1/generate-seo-content`.

    Le endpoint ne vit pas sous `/wp/v2` : on dérive la racine `/wp-json` de
    l'`api_base_url` du site plutôt que d'ajouter une clé de config que le
    reste du projet n'utiliserait pas.
    """

    _RETRY_STATUS = {429, 500, 502, 503, 504}

    def __init__(self, api_base_url: str, user_env_var: str, password_env_var: str,
                 timeout: int = 120):
        root = api_base_url.rstrip("/")
        root = re.sub(r"/wp/v2/?$", "", root)
        self.endpoint = f"{root}/sp/v1/generate-seo-content"
        self.timeout = timeout

        user = os.getenv(user_env_var)
        pwd = os.getenv(password_env_var)
        if not user or not pwd:
            raise ValueError(
                f"Identifiants WordPress absents : renseigner {user_env_var} "
                f"et {password_env_var}."
            )
        self._auth = (user, pwd)

    def generate(self, step: str, keyword: str, post_id: Optional[int] = None,
                 title: Optional[str] = None, h1: Optional[str] = None,
                 max_attempts: int = 3) -> Suggestion:
        """Une étape de la cascade. Ne sauvegarde rien côté WordPress."""
        sug = Suggestion(step=step, keyword=keyword)
        payload: dict = {"type": step}
        if keyword:
            payload["keyword"] = keyword
        if post_id:
            payload["post_id"] = post_id
        # Le plugin exige les étapes amont : title pour h1, title+h1 pour la
        # meta description. On les passe explicitement au lieu de compter sur
        # ce qui serait déjà enregistré sur le post.
        if title:
            payload["title"] = title
        if h1:
            payload["h1"] = h1

        for attempt in range(1, max_attempts + 1):
            try:
                resp = requests.post(
                    self.endpoint, json=payload, auth=self._auth,
                    timeout=self.timeout,
                    headers={"User-Agent": "ContentWriter/1.0"},
                )
                if resp.status_code == 200:
                    sug.options = self._extract(resp.json())
                    if not sug.options:
                        sug.error = f"réponse sans proposition : {str(resp.json())[:200]}"
                    return sug

                # Un 4xx (hors 429) est un refus de payload — le rejouer
                # rejouerait la même erreur. Même politique que update_post :
                # un 403 n'est jamais réessayé (WAF ou mot de passe révoqué).
                if resp.status_code not in self._RETRY_STATUS:
                    sug.error = self._message(resp)
                    return sug
                sug.error = self._message(resp)
            except requests.RequestException as e:
                sug.error = str(e)[:200]

            if attempt < max_attempts:
                delay = min(2 ** attempt, 30)
                logger.warning("generate %s '%s' échoue (essai %d/%d), reprise dans %ss",
                               step, keyword, attempt, max_attempts, delay)
                time.sleep(delay)
        return sug

    @staticmethod
    def _extract(data) -> list[str]:
        """Sort la liste de propositions, quelle que soit la clé employée.

        Le plugin nomme son tableau selon l'étape (`titles`, `headings`, …) ;
        on accepte n'importe quelle liste de chaînes plutôt que de coder en dur
        trois noms qu'une mise à jour du plugin pourrait changer.
        """
        if isinstance(data, list):
            return [str(x) for x in data if isinstance(x, str)]
        if isinstance(data, dict):
            for key in ("titles", "headings", "descriptions", "meta_descriptions",
                        "results", "content", "suggestions"):
                v = data.get(key)
                if isinstance(v, list) and v:
                    return [str(x) for x in v if isinstance(x, str)]
                if isinstance(v, str) and v.strip():
                    return [v.strip()]
            for v in data.values():
                if isinstance(v, list) and v and all(isinstance(x, str) for x in v):
                    return [str(x) for x in v]
        return []

    @staticmethod
    def _message(resp) -> str:
        try:
            body = resp.json()
            msg = body.get("message") or body.get("code") or ""
            # Le plugin préfixe ses messages d'un emoji d'alerte : inutile ici.
            return f"HTTP {resp.status_code}: {re.sub(r'^[^A-Za-z]+', '', str(msg))[:200]}"
        except Exception:
            return f"HTTP {resp.status_code}: {resp.text[:200]}"


def generate_row(gen: SeoTagGenerator, main_keyword: str, secondary_keyword: str,
                 post_id: Optional[int] = None) -> dict[str, Suggestion]:
    """La cascade complète d'une ligne : title (main KW) → h1 (secondary KW) → meta.

    Chaque étape alimente la suivante avec la valeur *retenue*, pas avec la
    première proposition brute : c'est ce que fait le parcours manuel quand tu
    choisis un titre avant de générer le H1.
    """
    steps: dict[str, Suggestion] = {}

    s_title = gen.generate(STEP_TITLE, main_keyword, post_id=post_id)
    s_title.chosen, s_title.rejected = _choose(s_title.options, main_keyword, STEP_TITLE)
    steps[STEP_TITLE] = s_title
    if not s_title.chosen:
        return steps

    # Le H1 se génère sur le mot-clé secondaire, en passant le title retenu
    # (exigé par le plugin). Sans secondary KW, l'étape n'a pas d'entrée.
    if not secondary_keyword:
        steps[STEP_H1] = Suggestion(step=STEP_H1, keyword="",
                                    error="mot-clé secondaire absent (colonne C)")
        return steps

    s_h1 = gen.generate(STEP_H1, secondary_keyword, post_id=post_id,
                        title=s_title.chosen)
    # Le main KW sert de référence orthographique : c'est lui qui porte la
    # forme correcte quand le secondary est une variante fautive.
    s_h1.chosen, s_h1.rejected = _choose(s_h1.options, secondary_keyword, STEP_H1,
                                         reference_keyword=main_keyword)

    # Un secondary KW fautif ou abrégé contamine les 5 propositions d'un coup
    # (le générateur le recopie verbatim). Plutôt que de laisser l'article sans
    # H1 — et de bloquer la meta description derrière —, on rejoue l'étape sur
    # le mot-clé principal, qui est propre dans 100 % des lignes observées.
    if not s_h1.chosen and secondary_keyword != main_keyword:
        retry = gen.generate(STEP_H1, main_keyword, post_id=post_id,
                             title=s_title.chosen)
        retry.chosen, retry.rejected = _choose(retry.options, main_keyword, STEP_H1)
        if retry.chosen:
            retry.rejected = s_h1.rejected + retry.rejected
            retry.fallback_from = secondary_keyword
            s_h1 = retry

    steps[STEP_H1] = s_h1
    if not s_h1.chosen:
        return steps

    # La meta description n'a pas de mot-clé propre dans le flux manuel : elle
    # découle du title et du H1. On garde le main KW comme graine.
    s_meta = gen.generate(STEP_META, main_keyword, post_id=post_id,
                          title=s_title.chosen, h1=s_h1.chosen)
    s_meta.chosen, s_meta.rejected = _choose(s_meta.options, main_keyword, STEP_META)
    steps[STEP_META] = s_meta
    return steps


# ---------------------------------------------------------------------------
# Lecture / écriture de la Sheet
# ---------------------------------------------------------------------------

def _col_letter(idx: int) -> str:
    letters = ""
    idx += 1
    while idx:
        idx, rem = divmod(idx - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def resolve_tab(site: str, tab_name: str, base_path: Optional[Path] = None) -> dict:
    """Le layout déclaré de l'onglet, avec les colonnes de sortie exigées.

    On refuse tôt un onglet qui ne déclare pas où écrire : « New Growing List »
    n'a pas de colonnes Title/H1/Metadescription, et deviner F/G/H y écrirait
    par-dessus « Impressions 12 mois ».
    """
    tp = SitePaths(base_path=base_path) if base_path else SitePaths()
    cfg = json.loads(tp.site_config(site).read_text(encoding="utf-8"))
    tabs = (cfg.get("sheets") or {}).get("tabs") or []
    for t in tabs:
        if t.get("name") == tab_name:
            return t
    known = ", ".join(repr(t.get("name")) for t in tabs)
    raise ValueError(f"Onglet {tab_name!r} non déclaré dans sheets.tabs du site "
                     f"{site}. Onglets connus : {known}")


def read_rows(client, tab: dict, tab_name: str, statuses: set[str],
              only_missing: bool = True) -> list[RowResult]:
    """Les lignes éligibles de l'onglet, numérotées comme Google Sheets les affiche."""
    rows = client._read_sheet(tab_name)
    if not rows:
        return []

    c_url = tab.get("col_url", 0)
    c_main = tab.get("col_keyword", 1)
    c_sec = tab.get("col_keyword_secondary", 2)
    c_status = tab.get("col_status")
    c_title = tab.get("col_title")
    header_rows = tab.get("header_row", 1)

    def cell(r, i):
        if i is None or i < 0 or len(r) <= i:
            return ""
        v = r[i]
        return v.strip() if isinstance(v, str) else str(v).strip()

    out: list[RowResult] = []
    for offset, row in enumerate(rows[header_rows:]):
        sheet_row = header_rows + offset + 1  # 1-based, en-têtes comprises
        url = cell(row, c_url)
        if not url.startswith("http"):
            continue

        res = RowResult(url=url, row=sheet_row,
                        main_keyword=cell(row, c_main),
                        secondary_keyword=cell(row, c_sec))

        if statuses and c_status is not None:
            if cell(row, c_status).strip().lower() not in statuses:
                continue
        if not res.main_keyword:
            res.skipped = "mot-clé principal absent (colonne B)"
        elif only_missing and c_title is not None and cell(row, c_title):
            # Déjà renseigné à la main : ne pas écraser un choix humain.
            continue
        out.append(res)
    return out


def write_sheet(client, tab: dict, tab_name: str, results: list[RowResult]) -> int:
    """Écrit les balises retenues dans les colonnes déclarées. Renvoie le nb de cellules."""
    cols = {STEP_TITLE: tab.get("col_title"),
            STEP_H1: tab.get("col_h1"),
            STEP_META: tab.get("col_metadesc")}
    missing = [s for s, c in cols.items() if c is None]
    if missing:
        raise ValueError(
            f"L'onglet {tab_name!r} ne déclare pas où écrire : "
            f"{', '.join('col_' + s.replace('-', '') for s in missing)} manquant(s) "
            f"dans sheets.tabs."
        )

    updates = []
    for r in results:
        for step, col in cols.items():
            val = r.value(step)
            if val:
                updates.append({"sheet": tab_name,
                                "cell": f"{_col_letter(col)}{r.row}",
                                "value": val})
    if not updates:
        return 0
    client._batch_update_cells(updates)
    return len(updates)


def push_to_seopress(site: str, results: list[RowResult],
                     base_path: Optional[Path] = None) -> list[dict]:
    """Pousse title + meta description dans SEOPress, article par article.

    Le H1 n'en fait pas partie : ce n'est pas une meta SEO mais le premier bloc
    du corps, que seul un refresh peut réécrire sans toucher au reste.
    """
    from scripts.utils.push_to_wp import build_client, resolve_wp_post_id

    client = build_client(site, base_path=base_path)
    out = []
    for r in results:
        meta = {key: r.value(step) for step, key in _PUSHABLE.items() if r.value(step)}
        if not meta:
            out.append({"url": r.url, "ok": False, "error": "rien à pousser"})
            continue

        pid = resolve_wp_post_id(r.url, base_path=base_path)
        post = client.get_post_by_id(pid) if pid else client.get_post_by_url(r.url)
        if not post:
            out.append({"url": r.url, "ok": False, "error": "post_not_found"})
            continue

        # `content=None` : on ne renvoie pas le corps. Un push de contenu reste
        # le travail de `finalize`/`push`, qui eux passent la garde de validation.
        res = client.update_post(post_id=post["id"], meta=meta)
        out.append({"url": r.url, "id": post["id"], "ok": res["ok"],
                    "error": res["error"]})
    return out
