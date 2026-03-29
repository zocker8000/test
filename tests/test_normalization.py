import unittest

from kickbase.bot.models import PlayerRecord
from kickbase.bot.normalization import normalize_club_label, normalize_player_name, normalize_player_record


class NormalizationTests(unittest.TestCase):
    def test_normalizes_player_name_whitespace_and_case(self) -> None:
        self.assertEqual(normalize_player_name("  Jamal   Musiala "), "jamal musiala")

    def test_normalizes_club_aliases_to_common_label(self) -> None:
        self.assertEqual(normalize_club_label("FC Bayern München"), "bayern münchen")
        self.assertEqual(normalize_club_label("Bayern Munich"), "bayern münchen")
        self.assertEqual(normalize_club_label("1. FC Köln"), "1. fc köln")
        self.assertEqual(normalize_club_label("Bayer 04 Leverkusen"), "bayer leverkusen")

    def test_normalizes_player_record_fields(self) -> None:
        record = PlayerRecord("1", "  Michael   Olise  ", club="FC Bayern München")

        normalized = normalize_player_record(record)

        self.assertEqual(normalized.name, "Michael Olise")
        self.assertEqual(normalized.club, "bayern münchen")


if __name__ == "__main__":
    unittest.main()
