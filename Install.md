# AI Quant Decision Core 安装说明

这份文件交给 Hermes 执行。目标是安装项目、配置 MCP，并完成基础验证。Python 和 Node 已由用户预装，不要重新安装。

## 定位项目目录

用户会把本文件和项目仓库一起提供给你。不要假设仓库位于固定路径，也不要使用其他机器的绝对路径。

1. 将当前工作目录设为本文件所在仓库根目录。
2. 确认根目录包含 `pyproject.toml`、`.env.example`、`src/ai_quant` 和 `skills.md`。
3. 所有命令从仓库根目录运行，使用相对路径。
4. 如果无法确定仓库根目录，先查找本文件位置，不要猜路径。

读取仓库根目录下的 `skills.md` 和 `skills/ai-quant/SKILL.md`。

## 检查环境

```powershell
python --version
node --version
npm --version
pip --version
```

要求 Python >= 3.11，Node >= 18。版本不满足时停止并报告，不要替换系统环境。

## 安装 Python 依赖

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,mcp]"
```

如果 PowerShell 禁止激活脚本：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

如果虚拟环境无法激活，也可以直接使用仓库内的解释器：

```text
.venv\Scripts\python.exe
```

## 创建配置

```powershell
Copy-Item .env.example .env
```

编辑仓库根目录下的 `.env` 文件。

至少填写：

```dotenv
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
JEV_BASE_URL=
JEV_API_KEY=
JEV_MODEL=jev-latest
MARKET_DATA_BASE_URL=https://api.binance.com
DATABASE_URL=sqlite:///./data/quant.db
SYMBOLS=BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT,DOGEUSDT
```

LLM 和 JEV 必须使用各自独立的 URL、Key 和 Model。不要把 Key 写入源码、Skill、日志或 MCP 描述。

## 验证项目

```powershell
$env:PYTHONPATH="src"
python -m compileall -q src
pytest -q
python -m ai_quant analyze BTCUSDT
```

如果 `pydantic`、`fastmcp` 或其他包缺失，重新执行：

```powershell
python -m pip install -e ".[dev,mcp]"
```

## 启动 MCP Server

```powershell
$env:PYTHONPATH="src"
python -m ai_quant.mcp
```

这是 stdio MCP Server，供 Hermes 连接。Hermes 使用虚拟环境时，command 指向当前仓库的 `.venv\Scripts\python.exe`。

```text
.venv\Scripts\python.exe
```

## Hermes MCP 配置

将 `<REPO_ROOT>` 替换为 Hermes 本次发现的仓库绝对路径：

```json
{
  "mcpServers": {
    "ai-quant": {
      "command": "<REPO_ROOT>/.venv/Scripts/python.exe",
      "args": ["-m", "ai_quant.mcp"],
      "cwd": "<REPO_ROOT>",
      "env": {"PYTHONPATH": "src"}
    }
  }
}
```

## Hermes 工作流

Hermes 先读取仓库根目录中的：

```text
skills.md
skills/ai-quant/SKILL.md
```

然后按此顺序工作：

```text
get_market_data(symbols, ["1h", "4h"], 7)
    -> 浏览器获取最近 7 天新闻和公告
    -> analyze_market(symbol, news, 7, ["1h", "4h"])
    -> LLM 总结新闻并挑选重要事件
    -> LLM 综合价格和重要新闻
    -> JEV 返回 LONG / SHORT / HOLD
    -> LLM 做最终判断和解释
```

新闻必须保留标题、来源、URL、发布时间、摘要、影响方向和 confidence。浏览器只能用于研究，禁止登录交易所、访问钱包、读取私钥或执行交易。

## MCP 工具

```text
get_market_data(symbols, intervals, lookback_days)
get_market_state(symbol)
analyze_market(symbol, news, lookback_days, intervals)
jev_decide(symbol, state)
get_prediction(symbol, limit)
get_predictions(symbols, limit)
```

## 完成报告

安装结束后汇报：

```text
[ ] Python / Node 版本通过
[ ] Python 依赖安装成功
[ ] .env 已创建
[ ] compileall 通过
[ ] pytest 结果
[ ] CLI 分析结果
[ ] MCP Server 可启动
[ ] Hermes MCP 配置已写入
[ ] skills.md 已读取
```

如果市场数据、LLM 或 JEV 请求失败，报告真实错误，不要伪造数据或方向。项目不包含任何真实交易能力。
