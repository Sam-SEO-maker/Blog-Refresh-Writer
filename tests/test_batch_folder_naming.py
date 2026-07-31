"""Le nom du dossier de lot doit trier chronologiquement.

Bug couvert (signalé le 2026-07-31) : `dated_batch_folder_name()` produisait
`articles_7_juillet_2026`, en toutes lettres et sans zéro-padding. Deux
conséquences :

- l'ordre alphabétique n'était pas l'ordre chronologique — « avril » avant
  « juillet » avant « mars » ;
- même à l'intérieur d'un mois, `articles_10_...` passait avant
  `articles_7_...`.

Format retenu : `articles_YYMMDD`, numérique et à largeur fixe.
"""

from datetime import datetime

from scripts.utils.output_manager import dated_batch_folder_name


class TestDatedBatchFolderName:

    def test_yymmdd_format(self):
        assert dated_batch_folder_name(datetime(2026, 7, 31)) == "articles_260731"

    def test_day_and_month_are_zero_padded(self):
        """Le padding est ce qui rend le tri fiable."""
        assert dated_batch_folder_name(datetime(2026, 4, 7)) == "articles_260407"

    def test_alphabetical_order_is_chronological(self):
        """La propriété qui motive tout le correctif."""
        dates = [
            datetime(2026, 12, 1),
            datetime(2026, 4, 7),
            datetime(2026, 7, 31),
            datetime(2027, 1, 3),
        ]
        names = [dated_batch_folder_name(d) for d in dates]
        assert sorted(names) == [dated_batch_folder_name(d) for d in sorted(dates)]

    def test_no_french_month_names(self):
        """L'ancien format ne doit pas revenir par mégarde."""
        for month in range(1, 13):
            name = dated_batch_folder_name(datetime(2026, month, 15))
            assert name == f"articles_26{month:02d}15"
            for word in ("janvier", "juillet", "decembre", "aout"):
                assert word not in name

    def test_defaults_to_now(self):
        name = dated_batch_folder_name()
        assert name.startswith("articles_")
        assert len(name) == len("articles_260731")
        assert name.removeprefix("articles_").isdigit()
