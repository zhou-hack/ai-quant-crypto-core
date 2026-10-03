# AI Quant Decision Core

## 开发文档 v0.1

## 1. 项目定位

开发一个独立的 **AI Quant Decision Core**。

当前阶段**只实现 LLM + JEV 这一层**，不实现交易执行、不实现真实交易、不部署 Hermes。

系统最终目标：

```text
Market Data
    ↓
LLM Research / Analysis
    ↓
Structured State
    ↓
JEV Decision
    ↓
LONG / SHORT / HOLD
```

未来由 Hermes 作为上层 Autonomous Research Agent 接入本项目。

最终形态：

```text
                    ┌─────────────────────┐
                    │       Hermes        │
                    │ Autonomous Research │
                    └──────────┬──────────┘
                               │
                         MCP + Skill
                               │
                               ▼
              ┌────────────────────────────┐
              │   AI Quant Decision Core   │
              │                            │
              │ Market Data                │
              │      ↓                     │
              │ LLM Analysis               │
              │      ↓                     │
              │ Structured State           │
              │      ↓                     │
              │ JEV Decision               │
              │      ↓                     │
              │ LONG / SHORT / HOLD        │
              └────────────────────────────┘
```

**本阶段不要实现 Hermes 本体。**

---

# 2. 核心设计原则

必须严格遵守以下职责：

### LLM

负责：

* 市场分析
* 新闻/事件分析
* 市场环境分析
* 结构化信息提取
* 生成 State
* 提供研究分析

LLM **不直接产生最终交易方向**。

---

### JEV

JEV 是纯 Decision Engine。

只负责：

```text
LONG
SHORT
HOLD
```

以及：

```text
confidence
```

JEV 不负责：

* 仓位
* 杠杆
* 止损
* 止盈
* 下单
* 投资组合
* 策略执行
* 自动修改策略

核心关系：

```text
State → JEV → Decision
```

---

### Quant / Risk / Execution

**本版本暂不实现。**

未来再作为独立模块加入。

---

### Hermes

**本版本不部署 Hermes。**

只准备：

1. MCP Server
2. Hermes Skill
3. 清晰的项目接口
4. 文档

确保未来 Hermes 可以直接读取项目并接入。

---

# 3. 当前版本范围

### 必须实现

```text
LLM Client
Market Data Client
Market State
State Builder
JEV Client
JEV Decision Pipeline
Prediction Storage
MCP Server
Hermes Skill
Configuration
Logging
Tests
```

### 当前版本禁止实现

```text
真实交易
交易所下单
Paper Trading
Portfolio Manager
Position Sizing
Leverage
Stop Loss
Take Profit
自动策略进化
自动修改 JEV
自动修改 Prompt
Hermes Agent 本体
```

不要为了“以后可能需要”提前实现这些功能。

---

# 4. Crypto 范围

第一版本支持最多 5 个 Crypto。

配置示例：

```yaml
symbols:
  - BTCUSDT
  - ETHUSDT
  - SOLUSDT
  - XRPUSDT
  - DOGEUSDT
```

要求：

```text
MAX_SYMBOLS = 5
```

系统应该允许用户通过配置修改币种。

---

# 5. 时间周期

主要目标：

```text
预测周期：1～3 天
```

市场数据可以支持：

```text
1m
5m
15m
1h
4h
1d
```

但第一版重点使用：

```text
1h
4h
```

不要强制交易。

系统只负责：

```text
获取数据
分析数据
做出 Decision
记录 Decision
```

---

# 6. LLM 配置

LLM 必须完全独立配置。

`.env`：

```dotenv
LLM_BASE_URL=https://example.com/v1
LLM_API_KEY=
LLM_MODEL=
```

禁止使用通用：

```dotenv
API_BASE_URL=
API_KEY=
MODEL=
```

LLM 必须拥有独立配置对象：

```python
settings.llm.base_url
settings.llm.api_key
settings.llm.model
```

---

# 7. JEV 配置

JEV 与 LLM 必须完全隔离。

`.env`：

```dotenv
JEV_BASE_URL=https://example.com
JEV_API_KEY=
JEV_MODEL=jev-latest
```

代码中必须：

```python
settings.jev.base_url
settings.jev.api_key
settings.jev.model
```

不得复用 LLM：

```python
settings.llm.base_url
settings.llm.api_key
```

也不得设计成：

```python
GenericAIClient
```

然后通过 provider 切换。

LLM Client 和 JEV Client 必须是两个独立 Client。

这样以后可以：

```text
LLM → Provider A
JEV → Provider B
```

完全互不影响。

---

# 8. `.env.example`

必须提供：

```dotenv
# =========================
# LLM
# =========================

LLM_BASE_URL=https://example.com/v1
LLM_API_KEY=
LLM_MODEL=


# =========================
# JEV
# =========================

JEV_BASE_URL=https://example.com
JEV_API_KEY=
JEV_MODEL=jev-latest


# =========================
# Market Data
# =========================

MARKET_DATA_BASE_URL=
MARKET_DATA_API_KEY=


# =========================
# Application
# =========================

APP_ENV=development
LOG_LEVEL=INFO

DATABASE_URL=sqlite:///./data/quant.db


# =========================
# Crypto
# =========================

SYMBOLS=BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT,DOGEUSDT
```

用户复制：

```bash
cp .env.example .env
```

然后自行修改。

`.env` 必须加入 `.gitignore`。

---

# 9. 配置文件

除了 `.env`，允许有：

```text
config/config.yaml
```

用于非敏感配置。

例如：

```yaml
market:
  interval: 1h
  max_symbols: 5

jev:
  choices:
    - LONG
    - SHORT
    - HOLD

analysis:
  horizon_hours:
    - 24
    - 48
    - 72
```

敏感信息只能来自 `.env`。

---

# 10. 项目结构

建议：

```text
ai-quant/
│
├── README.md
├── LICENSE
├── pyproject.toml
├── .env.example
├── .gitignore
│
├── config/
│   └── config.yaml
│
├── src/
│   └── ai_quant/
│       ├── __init__.py
│       │
│       ├── config/
│       │   └── settings.py
│       │
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── client.py
│       │   └── analyzer.py
│       │
│       ├── jev/
│       │   ├── __init__.py
│       │   ├── client.py
│       │   └── decision.py
│       │
│       ├── market/
│       │   ├── __init__.py
│       │   ├── client.py
│       │   ├── candles.py
│       │   └── state.py
│       │
│       ├── pipeline/
│       │   ├── __init__.py
│       │   └── analysis.py
│       │
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── database.py
│       │   └── models.py
│       │
│       └── mcp/
│           ├── __init__.py
│           ├── server.py
│           └── tools/
│               ├── market.py
│               ├── analysis.py
│               └── jev.py
│
├── skills/
│   └── ai-quant/
│       ├── SKILL.md
│       └── references/
│           ├── architecture.md
│           ├── tools.md
│           └── workflow.md
│
├── tests/
│   ├── test_config.py
│   ├── test_llm.py
│   ├── test_jev.py
│   ├── test_state.py
│   ├── test_pipeline.py
│   └── test_mcp.py
│
└── data/
    └── .gitkeep
```

---

# 11. LLM Client

使用 HTTP Client。

推荐：

```text
httpx
```

LLM API 默认按照 OpenAI-compatible API 设计。

接口：

```python
class LLMClient:

    async def chat(
        self,
        messages: list[dict],
        *,
        model: str | None = None,
        temperature: float = 0.2,
    ) -> str:
        ...
```

默认：

```python
model = settings.llm.model
base_url = settings.llm.base_url
api_key = settings.llm.api_key
```

不得硬编码 Provider。

---

# 12. LLM Analysis

LLM 的工作：

```text
Market Data
+
News/Event Data
+
Cross Asset Context
        ↓
       LLM
        ↓
Structured Analysis
```

LLM 输出必须尽量结构化。

建议内部模型：

```python
class LLMAnalysis(BaseModel):
    trend: float
    fundamental: float
    risk: float
    event: float
    sentiment: float
    summary: str
```

数值字段：

```text
0.0 ～ 1.0
```

但注意：

这些是 **LLM 分析结果**，不是 JEV 的结果。

---

# 13. State Builder

State Builder 将：

```text
Market Data
LLM Analysis
Cross Asset Data
```

组合成统一 State。

例如：

```json
{
  "symbol": "BTCUSDT",

  "market": {
    "price": 100000,
    "volume": 123456,
    "volatility": 0.31,
    "volume_zscore": 1.82
  },

  "technical": {
    "rsi": 67.2,
    "momentum": 0.72
  },

  "derivatives": {
    "funding_rate": 0.0001,
    "open_interest": 123456789
  },

  "llm_analysis": {
    "trend": 0.81,
    "fundamental": 0.63,
    "risk": 0.21,
    "event": 0.74,
    "sentiment": 0.68
  },

  "market_context": {
    "market_regime": "bullish",
    "btc_strength": 0.73
  }
}
```

State Builder 不允许产生：

```text
BUY
SELL
LONG
SHORT
```

它只负责构建 State。

---

# 14. JEV Client

JEV 是独立 HTTP Client。

接口：

```python
class JEVClient:

    async def models(self):
        ...

    async def decide(
        self,
        *,
        state: dict,
        question: dict,
        model: str | None = None,
    ):
        ...
```

API：

```text
POST {JEV_BASE_URL}/v1/systemone
```

认证：

```text
Authorization: Bearer {JEV_API_KEY}
```

不要复用 LLM HTTP Client 的认证配置。

可以复用底层 HTTP 库，但：

```text
LLMClient
JEVClient
```

必须是两个独立类。

---

# 15. JEV Decision

第一版本只有：

```text
LONG
SHORT
HOLD
```

问题：

```text
Based on the provided market state,
what is the most appropriate directional decision
for the next 1-3 days?

Choices:

LONG
SHORT
HOLD
```

JEV 不应该看到：

```text
账户余额
仓位
杠杆
止损
交易所 API
```

JEV 只看到：

```text
Market State
```

---

# 16. 内部 Decision Model

统一转换为：

```python
class JEVDecision(BaseModel):

    symbol: str

    direction: Literal[
        "LONG",
        "SHORT",
        "HOLD"
    ]

    confidence: float

    model: str

    timestamp: datetime
```

例如：

```json
{
  "symbol": "BTCUSDT",
  "direction": "LONG",
  "confidence": 0.73,
  "model": "jev-latest",
  "timestamp": "2026-10-03T12:00:00Z"
}
```

---

# 17. 五币联合 Context

LLM 可以同时看到最多 5 个币。

例如：

```text
BTCUSDT
ETHUSDT
SOLUSDT
XRPUSDT
DOGEUSDT
```

构造：

```json
{
  "assets": [...],
  "cross_asset": {
    "btc_strength": 0.73,
    "altcoin_strength": 0.61,
    "market_breadth": 0.68,
    "correlation_regime": "high"
  }
}
```

JEV 仍然对单个 symbol 做最终：

```text
LONG / SHORT / HOLD
```

---

# 18. Analysis Pipeline

核心 Pipeline：

```text
1. 获取 Market Data
        ↓
2. 获取需要的 News/Event Data
        ↓
3. 构建 Market Context
        ↓
4. LLM Analysis
        ↓
5. State Builder
        ↓
6. JEV Decision
        ↓
7. 保存 Prediction
        ↓
8. 返回结果
```

封装：

```python
class AnalysisPipeline:

    async def analyze(
        self,
        symbol: str,
    ) -> AnalysisResult:
        ...
```

最终：

```python
AnalysisResult(
    state=...,
    llm_analysis=...,
    jev_decision=...
)
```

---

# 19. Prediction Storage

必须记录每次 JEV 判断。

第一版 SQLite。

至少保存：

```text
id
timestamp
symbol

state_snapshot
llm_analysis

jev_model
jev_direction
jev_confidence

horizon
```

未来可以增加：

```text
future_1h_return
future_4h_return
future_24h_return
future_72h_return
```

但第一版至少要保证原始 prediction 完整保存。

**必须保存 State Snapshot。**

不能只保存：

```text
BTC → LONG
```

否则以后无法研究 JEV 为什么当时做出这个判断。

---

# 20. MCP Server

使用 MCP。

推荐：

```text
FastMCP
```

第一版只提供以下 Tools。

### `get_market_state`

获取当前市场 State。

参数：

```json
{
  "symbol": "BTCUSDT"
}
```

---

### `analyze_market`

执行：

```text
Market Data
→ LLM
→ State
→ JEV
```

参数：

```json
{
  "symbol": "BTCUSDT"
}
```

返回：

```json
{
  "symbol": "BTCUSDT",
  "state": {},
  "llm_analysis": {},
  "jev_decision": {
    "direction": "LONG",
    "confidence": 0.73
  }
}
```

---

### `jev_decide`

直接对已经存在的 State 调用 JEV。

参数：

```json
{
  "symbol": "BTCUSDT",
  "state": {}
}
```

---

### `get_prediction`

查询历史 JEV Prediction。

参数：

```json
{
  "symbol": "BTCUSDT",
  "limit": 20
}
```

---

### `get_predictions`

允许查询多个币。

---

# 21. MCP 不允许提供的 Tool

当前版本禁止：

```text
place_order
cancel_order
execute_trade
change_risk
enable_live_trading
```

这些 Tool 根本不要实现。

未来如果加入真实交易，也必须作为完全独立模块。

---

# 22. Hermes Skill

创建：

```text
skills/ai-quant/SKILL.md
```

内容应该告诉未来 Hermes：

```text
You are interacting with AI Quant Decision Core.

The system provides:

- Market State
- LLM Analysis
- JEV Decision
- Historical Predictions

LLM is responsible for research and analysis.

JEV is responsible only for directional decision:

LONG
SHORT
HOLD

The system does not execute real trades.

Do not assume that LONG means an order should be placed.

Do not attempt to bypass system constraints.
```

Skill 只描述：

```text
这个项目是什么
有哪些 MCP Tools
怎么使用
返回值是什么意思
```

不要在 Skill 里面实现 Hermes。

---

# 23. Hermes 接入目标

未来 Hermes 只需要：

```text
读取 SKILL.md
+
连接 MCP Server
```

即可使用。

目标体验：

```text
Hermes
   ↓
ai-quant MCP
   ↓
analyze_market
   ↓
LLM
   ↓
JEV
   ↓
Decision
```

**不得要求修改 Hermes 源代码。**

---

# 24. CLI

建议提供：

```bash
python -m ai_quant
```

以及：

```bash
python -m ai_quant.mcp
```

方便未来 Hermes 使用 stdio MCP。

可以提供：

```bash
python -m ai_quant analyze BTCUSDT
```

直接进行一次分析。

例如：

```text
$ python -m ai_quant analyze BTCUSDT

BTCUSDT

LLM Analysis:
trend:       0.81
fundamental: 0.63
risk:        0.21
event:       0.74

JEV:
direction:   LONG
confidence:  0.73
```

---

# 25. Logging

统一日志。

例如：

```text
INFO  market BTCUSDT data updated
INFO  llm analysis completed
INFO  state built
INFO  jev decision LONG confidence=0.73
INFO  prediction saved id=123
```

API Key 禁止出现在日志中。

---

# 26. Error Handling

LLM API 失败：

```text
不要调用 JEV
```

Market Data 失败：

```text
不要生成新的 State
```

JEV 失败：

```text
返回明确错误
不要伪造 Decision
```

任何 API 返回异常：

```text
不得 fallback 到一个假的 LONG/SHORT/HOLD
```

---

# 27. 测试

至少实现：

```text
test_config
test_llm_client
test_jev_client
test_state_builder
test_pipeline
test_prediction_storage
test_mcp
```

必须测试：

### LLM/JEV 配置隔离

```text
LLM_BASE_URL != JEV_BASE_URL
LLM_API_KEY != JEV_API_KEY
```

必须正常。

### JEV 错误

JEV API 返回 500：

```text
pipeline 必须失败
不能生成虚假 decision
```

### State

必须保证：

```text
0 <= trend <= 1
0 <= risk <= 1
```

等结构合法。

---

# 28. 安全

`.env`：

```text
禁止提交 Git
```

`.gitignore`：

```text
.env
*.db
data/*
__pycache__/
.venv/
```

API Key：

```text
绝对不能写入源码
绝对不能写入 Skill
绝对不能写入 MCP description
绝对不能写入日志
```

---

# 29. 第一阶段完成定义

当以下全部成立时，认为 v0.1 完成：

```text
[✓] LLM 可配置
[✓] JEV 可配置
[✓] LLM/JEV API 完全独立
[✓] Market Data 可获取
[✓] 最多 5 个币
[✓] LLM 可以分析
[✓] State Builder 正常工作
[✓] JEV 可以返回 LONG/SHORT/HOLD
[✓] Prediction 可以保存
[✓] MCP Server 可以运行
[✓] MCP 可以调用 analyze_market
[✓] Skill 已提供
[✓] Hermes 无需修改源码即可未来接入
[✓] 没有真实交易功能
[✓] 没有 Hermes 本体
```

---

# 30. 后续版本，不要现在实现

未来再开发：

```text
v0.2
Backtest

v0.3
Paper Trading

v0.4
Quant / Portfolio / Risk

v0.5
Hermes Autonomous Research

v0.6
Experiment Engine

v0.7
Strategy Evolution

v1.0
Production Trading
```

这些版本必须建立在 v0.1 的稳定 API 之上。

不要提前污染 v0.1。

---

# 31. 最终架构原则

整个项目必须遵守：

```text
LLM
= Research / Analysis

JEV
= Decision

Quant
= Future Position Calculation

Risk
= Future Hard Constraint

Execution
= Future Trading

Hermes
= Future Autonomous Researcher
```

当前：

```text
             AI Quant Core
                  │
        ┌─────────┴─────────┐
        ↓                   ↓
       LLM                 JEV
        │                   │
   Analysis             Decision
        └─────────┬─────────┘
                  ↓
              Prediction
                  ↓
              SQLite
                  │
                  ↓
                 MCP
                  │
                  ↓
           Future Hermes
```

**不要把这些职责混在一起。**

尤其：

> **JEV 只判断，不研究；LLM 负责分析，不直接交易；当前项目不执行交易。**

---

# 32. Codex 执行要求

请按照本文档实现项目。

开发时：

1. 优先实现最小可运行版本。
2. 不提前实现未来版本功能。
3. 不添加真实交易能力。
4. 不部署 Hermes。
5. 不修改 Hermes 源码。
6. LLM 与 JEV 必须使用完全独立的 `BASE_URL / API_KEY / MODEL`。
7. 所有 API Key 只能来自 `.env`。
8. 使用 Pydantic 定义内部数据模型。
9. 使用 async HTTP。
10. MCP 使用 stdio 优先。
11. 为核心模块编写测试。
12. 完成后提供：

* README
* `.env.example`
* MCP 配置示例
* Hermes Skill
* 启动命令
* 测试命令

最终必须做到：

```bash
cp .env.example .env
# 修改 LLM/JEV 配置

python -m ai_quant analyze BTCUSDT
```

以及：

```bash
python -m ai_quant.mcp
```

能够作为 MCP Server 被未来 Hermes 直接接入。

**本项目当前不是交易机器人，而是一个独立的 AI Quant Decision Core。**
