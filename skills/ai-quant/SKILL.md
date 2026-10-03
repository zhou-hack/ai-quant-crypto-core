# AI Quant Decision Core

You are interacting with an AI Quant Decision Core. Read the full guide in the repository root file `skills.md` before using the tools.

Hermes owns browser-based news research. Use an isolated browser or VM, search recent news and official announcements, and preserve source URLs and timestamps. Send the raw news to the LLM first; the LLM must summarize it and select the important events before the news enters Market State and JEV. The Core owns recent price data, structured state, LLM analysis, JEV decisions, and prediction storage.

Default research window: the latest 7 days, using 1h and 4h price data. After JEV returns, send its result back to the LLM for the final judgment and explanation. Preserve the original JEV direction and confidence. Never execute trades or access wallets, exchange accounts, private keys, order APIs, or API permission settings.

Use `get_market_data` to retrieve recent candles when Hermes needs raw prices. Pass browser-collected, source-attributed news to `analyze_market` through its `news` argument. The analysis result includes the original JEV decision and an LLM `decision_review`; keep both visible in the final report.

## Tools

- `get_market_state(symbol)`: read the latest stored state.
- `analyze_market(symbol)`: fetch market data, run LLM analysis, build state, ask JEV, and save the prediction.
- `jev_decide(symbol, state)`: ask JEV for a decision from an existing state.
- `get_prediction(symbol, limit)`: query a symbol's historical predictions.
- `get_predictions(symbols, limit)`: query predictions for multiple symbols.

LLM is responsible for research and analysis. JEV is responsible only for a directional decision: `LONG`, `SHORT`, or `HOLD`, with confidence. A LONG or SHORT result is an analytical output and does not place an order. This system has no real trading or execution tools.
