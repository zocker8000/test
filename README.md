# Bundesliga Ranking Bot

## Quick Start
```bash
cd /Users/dominique/Documents/Kickbase
python3 main.py --live
```

## Shareable Setup
- Real secrets are not committed.
- The repository includes placeholder files in [`.secrets/`](/Users/dominique/Documents/Kickbase/.secrets/) so the project can be shared safely.
- Replace [`/Users/dominique/Documents/Kickbase/.secrets/openai_api_key.txt`](/Users/dominique/Documents/Kickbase/.secrets/openai_api_key.txt) with a real OpenAI API key on your machine if you want LLM explanations.
- The placeholder value is `REPLACE_WITH_OPENAI_API_KEY`.
- Keep any additional local credentials inside `.secrets/` and do not commit real values.

## Purpose
Rank all 1. Bundesliga players with Kickbase market value > 500000.

## Non-goals
- no Kickbase API integration
- no LLM-first architecture

## Main workflow
1. load Bundesliga player pool
2. load or resolve market values
3. filter eligible players
4. enrich with web signals
5. compute deterministic ranking
6. optionally generate compact AI summaries

## Run targets
- fetch player pool
- fetch market values
- build normalized dataset
- build ranking
- export ranking

## Quick retrieval test
- `python3 main.py --source-url https://example.com/feed.json`
- If the feed is wrapped in an object, add `--source-list-key players`
- If field names differ, add repeated mappings like `--field-map name=title --field-map market_value=value`

## Live sources
- `python3 main.py --live`
- Uses the configured real sources in [`config/feeds.yaml`](/Users/dominique/Documents/Kickbase/config/feeds.yaml)
- Live runs print a pipeline status of `ready`, `degraded`, or `blocked`

## Caching
- External source responses are cached under `.cache/source_responses`
- Delete that directory if you want to force a full refetch

## Output
- Ranking results are written to `out/ranking.json` by default
- A CSV export is written alongside it as `out/ranking.csv`
- Override with `--output path/to/file.json`
- The JSON export includes `pipeline_status`, `pipeline_warnings`, and `source_player_counts`
- Transfermarkt market values fall back to `config/snapshots/transfermarkt_market_values_snapshot.json` when live loading fails

## Optional LLM
- Enabled by default via [`config/llm.yaml`](/Users/dominique/Documents/Kickbase/config/llm.yaml)
- Store the API token in `.secrets/openai_api_key.txt`
- The LLM only receives compact summaries of already computed rankings
- The API call result is written to `out/llm_response.json` only when a real API key is present
- There is no CLI switch for toggling the LLM

## Display selection
- The bot always shows up to 100 players
- There is no interactive question and no `--top` option anymore

## Smoke test script
- `bash scripts/smoke_test.sh`
- Optional live mode: `LIVE=1 bash scripts/smoke_test.sh`
