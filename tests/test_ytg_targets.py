"""Une cible absente n'est pas une cible atteinte.

Bug couvert (constaté en production le 2026-07-30, lot « Medium Potential ») :
`YTGQualityCheck` ne comparait qu'aux moyennes **TOP 3**, et traitait une cible
nulle comme un succès :

    result.dseo_ok = (result.our_dseo <= target_d) if target_d else True

Un guide dont le TOP 3 valait 0 — quota API épuisé, ou SERP dont les premières
positions ne traitent pas le sujet — validait donc n'importe quel contenu.
Deux articles du lot ont été déclarés OPTIMAL alors qu'ils étaient
sur-optimisés (« histoire du ski » à DSEO 9 pour une cible réelle de 1,3 ;
« cours diode zener » à DSEO 47 pour 13,5), et ont dû être repris à la main.

Le CLAUDE.md impose de se comparer aux moyennes TOP 3 **et** TOP 10 :
SOSEO au-dessus des deux, DSEO strictement sous les deux.
"""

from scripts.audit.ytg_qc import YTGQualityCheck


class TestResolveTargets:

    def test_strictest_of_both_averages(self):
        """SOSEO : la plus haute. DSEO : la plus basse."""
        soseo, dseo = YTGQualityCheck.resolve_targets(33.3, 9.0, 42.5, 13.3)
        assert soseo == 42.5, "il faut dépasser le TOP 10, plus exigeant ici"
        assert dseo == 9.0, "il faut rester sous le TOP 3, plus exigeant ici"

    def test_null_top3_falls_back_on_top10(self):
        """Cas « cours diode zener » : TOP 3 absent, TOP 10 exploitable.

        L'ancien code renvoyait OPTIMAL d'office ; la cible réelle est le TOP 10.
        """
        soseo, dseo = YTGQualityCheck.resolve_targets(0.0, 0.0, 41.8, 13.5)
        assert (soseo, dseo) == (41.8, 13.5)

    def test_all_null_yields_no_target(self):
        """Guide muet (quota API) : indéterminable, surtout pas « atteint »."""
        assert YTGQualityCheck.resolve_targets(0.0, 0.0, 0.0, 0.0) == (None, None)
        assert YTGQualityCheck.resolve_targets(None, None, None, None) == (None, None)

    def test_degenerate_top3_is_discarded(self):
        """Cas « centre de poussée » : TOP 3 = 5.0/0.7 contre TOP 10 = 32.4/8.8.

        Les trois premières positions ne traitent pas le sujet ; leur DSEO
        proche de 0 imposerait une cible inatteignable. Le TOP 10 fait seul foi.
        """
        soseo, dseo = YTGQualityCheck.resolve_targets(5.0, 0.7, 32.4, 8.8)
        assert (soseo, dseo) == (32.4, 8.8), "le TOP 3 dégénéré doit être écarté"

    def test_healthy_top3_is_kept(self):
        """Cas « optique MPSI » : TOP 3 et TOP 10 cohérents, les deux comptent."""
        soseo, dseo = YTGQualityCheck.resolve_targets(32.7, 11.3, 34.4, 11.6)
        assert (soseo, dseo) == (34.4, 11.3)

    def test_ratio_boundary_keeps_top3(self):
        """Juste au-dessus du seuil : le TOP 3 reste représentatif."""
        # ratio = 0.5 → 20.0 n'est pas < 40.0 * 0.5
        soseo, dseo = YTGQualityCheck.resolve_targets(20.0, 2.0, 40.0, 8.0)
        assert dseo == 2.0, "TOP 3 au seuil : conservé, donc DSEO le plus strict"


class TestNoFalseOptimal:
    """Le scénario exact des deux faux positifs du lot."""

    def test_ski_case_is_no_longer_optimal(self):
        """DSEO 9 contre une cible TOP 10 de 1,3 : ce n'est pas OPTIMAL."""
        soseo, dseo = YTGQualityCheck.resolve_targets(5.3, 0.0, 24.9, 1.3)
        our_soseo, our_dseo = 67.0, 9.0
        assert our_soseo >= soseo
        assert not (our_dseo <= dseo), "l'ancien code validait ce cas à tort"

    def test_zener_case_is_no_longer_optimal(self):
        """DSEO 47 contre une cible de 13,5."""
        _, dseo = YTGQualityCheck.resolve_targets(0.0, 0.0, 41.8, 13.5)
        assert not (47.0 <= dseo), "l'ancien code validait ce cas à tort"

    def test_genuine_optimal_still_passes(self):
        """Après correction, l'article corrigé passe légitimement."""
        soseo, dseo = YTGQualityCheck.resolve_targets(0.0, 0.0, 41.8, 13.5)
        assert 52.0 >= soseo and 5.0 <= dseo


class TestRecommendedRanges:
    """La zone verte de YTG (`Recommended score`) prime sur les moyennes SERP.

    Mesuré le 14/08/2026 sur « majorée et minorée » : 4 résultats SERP sur 9
    (3 YouTube + 1 page sans texte) scoraient 0/0 et tiraient la cible DSEO à
    10,3, quand le guide recommandait 0-27. Le pipeline visait donc 2 à 3 fois
    plus sévère que l'outil lui-même.
    """

    @staticmethod
    def _guide(**kw):
        from types import SimpleNamespace
        base = dict(reco_soseo_min=None, reco_soseo_max=None,
                    reco_dseo_min=None, reco_dseo_max=None,
                    top3_soseo=0.0, top3_dseo=0.0,
                    top10_soseo=0.0, top10_dseo=0.0)
        base.update(kw)
        return SimpleNamespace(**base)

    def test_recommended_range_wins_over_serp_averages(self):
        g = self._guide(reco_soseo_min=85, reco_soseo_max=102,
                        reco_dseo_min=0, reco_dseo_max=27,
                        top3_soseo=25.7, top3_dseo=10.3,
                        top10_soseo=41.6, top10_dseo=13.6)
        assert YTGQualityCheck.resolve_ranges(g) == (85, 102, 0.0, 27)

    def test_falls_back_to_serp_when_guide_is_silent(self):
        """Guide sans plages : on retombe sur les moyennes, sans inventer de max."""
        g = self._guide(top3_soseo=60.0, top3_dseo=8.0,
                        top10_soseo=50.0, top10_dseo=12.0)
        s_min, s_max, d_min, d_max = YTGQualityCheck.resolve_ranges(g)
        assert (s_min, d_max) == (60.0, 8.0)
        assert s_max is None, "aucun maximum ne doit être inventé"


class TestActionFromRange:
    """Le verdict dit quoi faire, pas seulement que ça ne va pas."""

    @staticmethod
    def _decide(our_soseo, our_dseo, s_min, s_max, d_min, d_max):
        """Reproduit la décision de `check_html` (zone verte + action)."""
        low = our_soseo < s_min
        high = bool(s_max) and our_soseo > s_max
        dseo_ok = d_min <= our_dseo <= d_max
        if not (low or high) and dseo_ok:
            return ""
        if high:
            return "ELAGUER"
        if low and dseo_ok:
            return "ENRICHIR"
        if our_dseo > d_max:
            return "REECRIRE"
        return "ENRICHIR"

    def test_soseo_above_max_means_prune(self):
        """volume-fraction-resolution : SOSEO 146 > 102 et DSEO 67 > 27."""
        assert self._decide(146, 67, 85, 102, 0, 27) == "ELAGUER"

    def test_soseo_below_min_means_enrich(self):
        """projet-redaction-ebauche : SOSEO 40 < 84, DSEO dans la plage."""
        assert self._decide(40, 10, 84, 101, 0, 32) == "ENRICHIR"

    def test_soseo_in_range_but_dseo_high_means_rewrite(self):
        """Couverture correcte, densité concentrée : réécrire à volume constant."""
        assert self._decide(70, 40, 65, 78, 0, 26) == "REECRIRE"

    def test_inside_both_ranges_is_optimal(self):
        """mecanique-deplacement : SOSEO 68 dans 65-78, DSEO 20 dans 0-26."""
        assert self._decide(68, 20, 65, 78, 0, 26) == ""
