# Project rules

## Goal
Build a Bundesliga player ranking bot without Kickbase API integration.
The bot must rank all 1. Bundesliga players with Kickbase market value above 500000.

## Priorities
1. Stable web/source ingestion
2. Deterministic ranking without AI
3. Reliable filtering by market value
4. Optional LLM explanations after the core pipeline works

## Constraints
- Minimize token usage.
- Do not use LLMs for primary ranking logic.
- Prefer local scoring over model inference.
- Cache all external source responses where possible.
- Every feature used in ranking must be testable.
- Keep source-specific scraping or API logic isolated in clients/.

## Execution rules
- First implement source validation and player matching.
- Then implement market value filtering.
- Then implement deterministic ranking.
- Add LLM support only after the non-LLM pipeline works end-to-end.
- Only send compact top-player summaries to the LLM.
