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
