import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from unittest.mock import patch

from kickbase.bot.llm import OptionalLLMClient, load_llm_config, read_api_key_from_file
from kickbase.bot.models import PlayerRecord, RankingThresholds, RankingWeights
from kickbase.bot.ranking import RankingService


class LLMConfigTests(unittest.TestCase):
    def test_defaults_to_enabled(self) -> None:
        config = load_llm_config("config/llm.yaml")

        self.assertTrue(config.enabled)
        self.assertEqual(config.max_players, 5)

    def test_reads_api_key_from_external_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            api_key_path = Path(tmpdir) / "openai_api_key.txt"
            api_key_path.write_text("secret-token\n", encoding="utf-8")

            self.assertEqual(read_api_key_from_file(str(api_key_path)), "secret-token")

            config_path = Path(tmpdir) / "llm.yaml"
            config_path.write_text(
                "llm:\n"
                "  enabled: true\n"
                f"  api_key_file: {api_key_path.as_posix()}\n"
                "  max_players: 3\n"
                "  prompt_token_budget: 120\n"
                "  response_token_budget: 80\n",
                encoding="utf-8",
            )

            client = OptionalLLMClient(config_path=str(config_path))

            self.assertTrue(client.is_enabled())
            self.assertEqual(client.api_key, "secret-token")
            self.assertEqual(client.config.max_players, 3)

    def test_ignores_placeholder_api_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            api_key_path = Path(tmpdir) / "openai_api_key.txt"
            api_key_path.write_text("REPLACE_WITH_OPENAI_API_KEY\n", encoding="utf-8")

            self.assertIsNone(read_api_key_from_file(str(api_key_path)))

            config_path = Path(tmpdir) / "llm.yaml"
            config_path.write_text(
                "llm:\n"
                "  enabled: true\n"
                f"  api_key_file: {api_key_path.as_posix()}\n",
                encoding="utf-8",
            )

            client = OptionalLLMClient(config_path=str(config_path))

            self.assertFalse(client.is_enabled())
            self.assertIsNone(client.api_key)

    @patch("kickbase.bot.llm.call_openai_responses_api")
    def test_generate_explanation_calls_openai_responses_api(self, mock_call) -> None:
        mock_call.return_value = {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": "Keep this player."},
                    ],
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            api_key_path = Path(tmpdir) / "openai_api_key.txt"
            api_key_path.write_text("real-secret-token\n", encoding="utf-8")

            config_path = Path(tmpdir) / "llm.yaml"
            config_path.write_text(
                "llm:\n"
                "  enabled: true\n"
                f"  api_key_file: {api_key_path.as_posix()}\n"
                "  api_base_url: https://example.com/v1/responses\n"
                "  model: gpt-4o-mini\n"
                "  max_players: 1\n"
                "  prompt_token_budget: 120\n"
                "  response_token_budget: 80\n",
                encoding="utf-8",
            )

            client = OptionalLLMClient(config_path=str(config_path))
            service = RankingService(
                RankingWeights(),
                RankingThresholds(minimum_market_value=500000, minimum_confidence=0.0),
            )
            ranked_players = service.rank(
                [
                    PlayerRecord(
                        "1",
                        "Test Player",
                        club="Test FC",
                        position="MF",
                        market_value=700000,
                        confidence=1.0,
                        signals={"market_value_signal": 1.0},
                    )
                ]
            )

            result = client.generate_explanation(ranked_players)

        self.assertIsNotNone(result)
        self.assertEqual(result.response_text, "Keep this player.")
        self.assertEqual(result.error, None)
        mock_call.assert_called_once()
        self.assertEqual(mock_call.call_args.kwargs["api_key"], "real-secret-token")
        self.assertEqual(mock_call.call_args.kwargs["base_url"], "https://example.com/v1/responses")
        self.assertEqual(mock_call.call_args.kwargs["request_payload"]["model"], "gpt-4o-mini")
        self.assertEqual(mock_call.call_args.kwargs["request_payload"]["max_output_tokens"], 80)
        self.assertIn("Players:", mock_call.call_args.kwargs["request_payload"]["input"][0]["content"][0]["text"])

    @patch("kickbase.bot.llm.urlopen")
    def test_openai_api_call_retries_on_rate_limit(self, mock_urlopen) -> None:
        class FakeResponse:
            def __init__(self, body: bytes) -> None:
                self.body = body

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return self.body

        mock_urlopen.side_effect = [
            HTTPError("https://example.com/v1/responses", 429, "Too Many Requests", hdrs=None, fp=None),
            FakeResponse(
                b'{"output":[{"type":"message","content":[{"type":"output_text","text":"Retry ok."}]}]}'
            ),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            api_key_path = Path(tmpdir) / "openai_api_key.txt"
            api_key_path.write_text("real-secret-token\n", encoding="utf-8")

            config_path = Path(tmpdir) / "llm.yaml"
            config_path.write_text(
                "llm:\n"
                "  enabled: true\n"
                f"  api_key_file: {api_key_path.as_posix()}\n"
                "  api_base_url: https://example.com/v1/responses\n"
                "  model: gpt-4o-mini\n"
                "  max_players: 1\n"
                "  prompt_token_budget: 120\n"
                "  response_token_budget: 80\n",
                encoding="utf-8",
            )

            client = OptionalLLMClient(config_path=str(config_path))
            service = RankingService(
                RankingWeights(),
                RankingThresholds(minimum_market_value=500000, minimum_confidence=0.0),
            )
            ranked_players = service.rank(
                [
                    PlayerRecord(
                        "1",
                        "Test Player",
                        club="Test FC",
                        position="MF",
                        market_value=700000,
                        confidence=1.0,
                        signals={"market_value_signal": 1.0},
                    )
                ]
            )

            result = client.generate_explanation(ranked_players)

        self.assertIsNotNone(result)
        self.assertEqual(result.response_text, "Retry ok.")
        self.assertEqual(mock_urlopen.call_count, 2)


if __name__ == "__main__":
    unittest.main()
