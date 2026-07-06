# Minimal Local Agent

这是一个分阶段实现的最小可用本地 Agent Demo。它可以在会话内接收用户输入，由 LLM 决策是否调用本地工具，并把工具结果整理为自然语言回答。

当前项目已包含：

- 工具基类和工具注册中心
- 计算器工具
- Mock 搜索工具
- 真实联网搜索工具
- 待办事项工具
- 会话内状态和 session 隔离
- FakeLLM 测试客户端
- 严格 JSON 决策协议
- 最小 Agent Runtime loop
- CLI 入口
- 受控上下文和基础摘要压缩
- 阿里云百炼 qwen3.7-plus OpenAI-compatible 接入
- CLI 友好异常提示
- 端到端测试

## 架构说明

```text
agent/
  __init__.py
  runtime.py
  session.py
  llm_client.py
config/
  local_llm.example.json
tests/
  __init__.py
  test_tools.py
  test_runtime.py
  test_e2e.py
tools/
  __init__.py
  registry.py
  calculator.py
  search.py
  todo.py
main.py
prompt_records.md(AI Prompt)
question-answer.md(架构设计题)
requirements.txt（环境）
README.md
```

核心模块：

- `agent/runtime.py`：执行 Agent loop，负责调用 LLM、解析 JSON 决策、调用工具、记录上下文。
- `agent/session.py`：保存 `SessionState`，包含消息、摘要、待办事项和工具调用记录。
- `agent/llm_client.py`：定义 `LLMClient`、`FakeLLM` 和 `AliyunBailianLLM`。
- `tools/registry.py`：定义 `BaseTool`、`ToolResult` 和 `ToolRegistry`。
- `main.py`：CLI 入口，优先使用阿里云百炼配置，缺少配置或依赖时回退到 RuleBasedLLM 演示模式。

## 工具列表

- `calculator`
  - 支持加、减、乘、除、括号和小数。
  - 使用 `ast` 做安全表达式解析。

- `mock_search`
  - 使用内置 mock 数据。
  - 不访问真实互联网。
  - 可搜索 Python、北京天气、苹果手机价格、Agent 工具注册中心等模拟内容。

- `web_search`
  - 使用 DuckDuckGo HTML 搜索访问真实互联网。
  - 当 HTML 页面没有解析出结果时，会使用 DuckDuckGo Instant Answer JSON 作为兜底。
  - 返回真实搜索结果的标题、链接、摘要和来源。
  - 网络不可用或搜索服务不可达时，会返回友好的工具错误。
  - 不需要额外 API Key。

- `todo`
  - 支持 `create`、`list`、`complete`、`delete`。
  - 数据保存在当前 `SessionState` 中。
  - 不同 `user_id + session_id` 的待办事项互相隔离。

## Runtime 流程

1. CLI 接收用户输入。
2. Runtime 获取或创建 `SessionState`。
3. Runtime 记录用户消息。
4. Runtime 将 session summary、最近消息和工具 schema 传给 LLM。
5. LLM 必须返回严格 JSON。
6. 如果 `action=tool`：
   - Runtime 从 `ToolRegistry` 获取工具。
   - 执行工具。
   - 记录 `tool_traces`。
   - 将工具结果加入上下文。
   - 继续下一轮 loop。
7. 如果 `action=final`：
   - Runtime 记录 assistant 消息。
   - 返回自然语言答案。
8. Runtime 使用 `max_steps` 避免死循环。
9. 当消息超过 `max_messages` 时，旧消息会被压缩进 `summary`。

LLM 输出只允许两种 JSON：

```json
{
  "action": "tool",
  "tool_name": "calculator",
  "arguments": {
    "expression": "1 + 2"
  }
}
```

```json
{
  "action": "final",
  "answer": "计算结果是 3。"
}
```

## 运行 CLI

创建虚拟环境并安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

启动 CLI：

```powershell
.\.venv\Scripts\python.exe main.py
```

CLI 默认使用：

- `user_id = local_user`
- `session_id = default`

输入 `exit` 或 `quit` 退出。

如果当前没有配置 `config/local_llm.json`，CLI 会自动使用 `RuleBasedLLM` 演示模式，适合本地离线演示计算器和待办事项。搜索请求会调用 `web_search`，需要本机能访问外网。

## 阿里云百炼配置

复制示例配置：

```powershell
copy config\local_llm.example.json config\local_llm.json
```

编辑 `config/local_llm.json`：

```json
{
  "api_key": "your-api-key-here"
}
```

注意：

- `config/local_llm.json` 已被 `.gitignore` 忽略。
- 不要提交真实 API Key。
- 如果该文件存在且包含 `api_key`，CLI 会优先使用阿里云百炼 qwen3.7-plus。
- 如果文件不存在、缺少 `api_key`，或本地缺少 `openai` 依赖，CLI 会给出提示并回退到 RuleBasedLLM 演示模式。
- 如果请求百炼时出现连接失败，CLI 会提示检查网络、代理、API Key 和服务地址。

## 示例对话

```text
> calculate 1 + 2 * 3
计算结果是 7。

> search Python
找到若干条真实联网搜索结果：...

> add todo submit report
待办 1：submit report，状态：未完成。

> list todo
当前待办：1. submit report (未完成)。

> complete 1
待办 1：submit report，状态：完成。
```

中文输入示例：

```text
计算 1 + 2 * 3
搜索 Python 是什么
添加待办 提交周报
查看待办
完成 1
删除 1
```

## 简短演示命令

运行 CLI 的计算和退出演示：

```powershell
@('calculate 1 + 2 * 3', 'quit') | .\.venv\Scripts\python.exe main.py
```

运行真实搜索工具的直接验证：

```powershell
.\.venv\Scripts\python.exe -c "from tools.search import WebSearchTool; r=WebSearchTool(timeout=10, max_results=2).run({'query': 'Python'}); print(r.success); print(r.error); print(r.data)"
```

## 运行测试

运行全部测试：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

测试覆盖：

- 工具注册中心
- 计算器工具
- Mock 搜索工具
- 真实联网搜索工具的 HTML 解析和异常处理
- 待办事项工具
- FakeLLM
- JSON 决策解析
- Agent Runtime loop
- 上下文压缩
- 阿里云百炼客户端的 mock 测试
- 端到端任务流

测试不会调用真实 LLM，也不会访问真实网络；真实搜索能力通过注入假 HTML/JSON 进行测试。

## 常见问题

- `Aliyun Bailian API request failed: Connection error.`
  - 检查本机网络、代理、API Key、百炼服务地址和 HTTPS 访问能力。

- `LLM 返回内容不是有效 JSON`
  - 当前 Runtime 要求 LLM 严格输出 JSON；可以重试，或检查 system prompt 是否被模型遵守。

- 搜索没有结果
  - `web_search` 依赖 DuckDuckGo 返回内容；不同网络环境下结果可能不同，失败时会返回工具错误或空结果提示。
