# Open Assumptions

- External sources are intentionally abstracted. The scaffold does not confirm concrete websites or APIs yet.
- Kickbase market values must be ingested without using the Kickbase API. The implementation point exists, but the concrete source adapter is still a placeholder.
- Ranking is deterministic and local first. LLM support is optional and only intended for compact explanations after the non-LLM pipeline is complete.
- `config/sources.yaml` is treated as a source registry, not as a claim that the listed sources are already implemented.
- The current implementation fetches live player data through confirmed Bundesliga and Transfermarkt adapters, but the upstream HTML layouts can still change without notice.
- Player matching uses normalized player name plus normalized club label, with a conservative fallback to name-only matching when club data is missing or ambiguous.
- Confidence is deterministic and derived from source agreement plus field completeness; it is not a learned model.
- A generic JSON feed adapter exists for testable data retrieval. It accepts a configurable URL and optionally a JSON key containing the player list; it does not assume any specific public source schema.
- The JSON adapter supports field aliases via `--field-map TARGET=SOURCE`, so feeds with keys like `id`, `title`, `team`, or `value` can be tested without code changes.
- Live ranking currently combines the official Bundesliga player pool and stats pages with Transfermarkt market values from the first four Bundesliga pages.
- External responses are cached locally to reduce repeat network requests and keep smoke tests more stable.
- `reported_at` is an optional ISO-like timestamp on player records for future news relevance scoring; most live sources do not currently provide it, but JSON feeds can map it in directly.
- `news_recency_signal()` currently stays separate from ranking; it is only a deterministic helper for future relevance weighting.
- Optional LLM usage is enabled by default and only receives compact, already-ranked player summaries together with a short explanation prompt.
- The LLM API token is read from `.secrets/openai_api_key.txt` so the repository can be shared without private credentials; placeholder values are treated as missing secrets and do not trigger an API call.
- If live Transfermarkt loading fails, the client falls back to the local snapshot file at `config/snapshots/transfermarkt_market_values_snapshot.json`.
