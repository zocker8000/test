import unittest

from kickbase.bot.llm import LLMConfig, build_llm_plan, compact_player_summary, estimate_prompt_tokens, select_prompt_players
from kickbase.bot.models import PlayerRecord, RankingThresholds, RankingWeights
from kickbase.bot.ranking import RankingService


class LLMPromptTests(unittest.TestCase):
    def _ranked_players(self):
        service = RankingService(
            RankingWeights(
                market_value_signal=0.2,
                form_signal=0.2,
                availability_signal=0.25,
                news_signal=0.1,
                news_recency_signal=0.0,
                trend_signal=0.15,
                value_opportunity_signal=0.1,
            ),
            RankingThresholds(minimum_market_value=500000, minimum_confidence=0.0),
        )

        return service.rank(
            [
                PlayerRecord(
                    "1",
                    "Michael Olise",
                    club="FC Bayern München",
                    position="FW",
                    market_value=140000000,
                    confidence=0.95,
                    signals={"market_value_signal": 1.0, "form_signal": 0.7},
                ),
                PlayerRecord(
                    "2",
                    "Harry Kane",
                    club="FC Bayern München",
                    position="FW",
                    market_value=110000000,
                    confidence=0.90,
                    signals={"market_value_signal": 0.9, "form_signal": 0.9},
                ),
            ]
        )

    def test_compact_player_summary_is_short_and_only_uses_ranked_data(self) -> None:
        ranked_player = self._ranked_players()[0]

        summary = compact_player_summary(ranked_player)

        self.assertIn(summary["name"], {"Michael Olise", "Harry Kane"})
        self.assertEqual(summary["club"], "FC Bayern München")
        self.assertIn("score", summary)
        self.assertLessEqual(len(summary["sig"]), 3)

    def test_prompt_builder_uses_precomputed_rankings_only(self) -> None:
        ranked_players = self._ranked_players()
        config = LLMConfig(
            enabled=True,
            api_key_file=".secrets/openai_api_key.txt",
            max_players=2,
            prompt_token_budget=220,
            response_token_budget=120,
        )

        plan = build_llm_plan(ranked_players, config=config, api_key="secret-token")

        self.assertTrue(plan.enabled)
        self.assertTrue(plan.api_key_loaded)
        self.assertIn("You are not ranking.", plan.prompt)
        self.assertIn("Do not reorder players.", plan.prompt)
        self.assertLessEqual(plan.prompt_tokens, config.prompt_token_budget)
        self.assertLessEqual(len(plan.player_summaries), 2)

    def test_token_budget_caps_player_count(self) -> None:
        ranked_players = self._ranked_players()
        config = LLMConfig(
            enabled=True,
            api_key_file=".secrets/openai_api_key.txt",
            max_players=5,
            prompt_token_budget=80,
            response_token_budget=120,
        )

        selected = select_prompt_players(ranked_players, config)

        self.assertEqual(len(selected), 1)


if __name__ == "__main__":
    unittest.main()
