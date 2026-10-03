# AI Quant Decision Core

独立的加密货币研究与方向决策核心。Hermes 负责浏览器新闻研究和任务编排，Core 获取最近市场数据，LLM 总结新闻并提名方向，JEV 作为辅助评分模型对 LLM 提名打分，score ≥ `JEV_SCORE_THRESHOLD` 才采纳，否则落 `HOLD`。最后由 LLM 对最终方向做解释。

本项目不执行真实交易，不包含下单、撤单、钱包、账户、仓位、杠杆、止损或止盈能力。

## 流程

```text
Hermes 新闻 -> 最近 7 天 1h / 4h 市场数据 -> LLM 筛选重要新闻
-> LLM 综合分析 + 提名方向 -> Market State -> JEV 评分
-> 若 score >= threshold：direction = LLM 提名，否则 direction = HOLD
-> LLM Final Judgment -> SQLite Prediction
```

## 安装

```bash
python -m venv .venv
pip install -e ".[dev,mcp]"
cp .env.example .env
# 编辑 .env 中的 LLM/JEV 配置
```

完整安装和 Hermes 接入说明见 [Install.md](Install.md)。

## 配置

LLM 和 JEV 必须使用独立的 URL、Key 和 Model。敏感信息只能放在 `.env`。

默认非敏感配置在 [config/config.yaml](config/config.yaml)：最近 7 天、`1h` / `4h`、最多 5 个币种。

## CLI

```powershell
$env:PYTHONPATH="src"
python -m ai_quant analyze BTCUSDT
```

## Standalone Scripts

The `scripts/` directory contains optional helpers that wrap the analysis
pipeline for one-off Telegram-style reports. They expect a populated `.env`
and a working venv interpreter at `.venv/Scripts/python.exe`.

```powershell
$env:PYTHONPATH="src"
python -m scripts.fetch_news --currencies BTC,ETH --hours 24
python -m scripts.run_analysis BTCUSDT
python -m scripts.run_analysis ETHUSDT --news-file path\to\news.json
```

- `scripts/fetch_news` aggregates BTC/ETH news from CryptoPanic + several
  RSS sources and writes a JSON list to stdout.
- `scripts/run_analysis` runs the full pipeline with optional pre-fetched
  news, formats a compact Telegram message, and prints it to stdout
  (Chinese translation ready when paired with an LLM that supports it).
- `scripts/run_analysis --news-file <path>` skips the HTTP fetcher and
  reads news from a JSON list — useful when news has been scraped by an
  external browser driver.

## MCP Server

```powershell
$env:PYTHONPATH="src"
python -m ai_quant.mcp
```

Hermes MCP 配置模板，将 `<REPO_ROOT>` 替换为实际仓库路径：

```json
{"mcpServers":{"ai-quant":{"command":"<REPO_ROOT>/.venv/Scripts/python.exe","args":["-m","ai_quant.mcp"],"cwd":"<REPO_ROOT>","env":{"PYTHONPATH":"src"}}}}
```

Hermes 推荐先调用 `get_market_data` 获取最近 7 天的 `1h`/`4h` 数据，再用浏览器收集带来源的新闻，最后调用：

```json
{
  "symbol": "BTCUSDT",
  "news": [],
  "lookback_days": 7,
  "intervals": ["1h", "4h"]
}
```

传给 `analyze_market`。LLM 会先筛选最多 5 条重要新闻，再提名方向；`jev_decision.score` 保留 JEV 原始评分，`jev_decision.direction` 是阈值采纳后的方向，`final_judgment` 是 LLM 最终解释并保留这两个值。

## Hermes 文档

先读取 `skills.md`、`skills/ai-quant/SKILL.md` 和 `Install.md`。新闻必须保留标题、来源、URL、发布时间、摘要、影响方向和 confidence。浏览器禁止用于交易所登录、钱包、私钥、API 权限或下单。

## 测试

```powershell
$env:PYTHONPATH="src"
python -m compileall -q src
pytest -q
```
