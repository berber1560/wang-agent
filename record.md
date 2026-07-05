# 项目阶段完成记录

## 第 1 阶段：建立项目骨架和最小运行入口

- 创建了最小可用本地 Agent 项目骨架：
  - `main.py`
  - `agent/`
  - `tools/`
  - `tests/`
  - `requirements.txt`
  - `README.md`
- 在 `main.py` 中实现了最小 CLI 循环：
  - 启动后提示用户输入。
  - 用户输入 `exit` 或 `quit` 时退出。
  - 其他输入会被原样回显。
- 在 `README.md` 中补充了项目目标、目录结构和运行方式。
- 当前阶段没有实现 Agent Runtime、工具逻辑或真实 LLM 接入。
- 验证命令：

```powershell
@('hello stage 1', 'quit') | .\.venv\Scripts\python.exe main.py
```

## 第 2 阶段：实现工具基类和工具注册中心

- 在 `tools/registry.py` 中实现了工具基础结构：
  - `BaseTool` 工具基类。
  - `ToolResult` 统一工具返回结构。
  - `ToolRegistry` 工具注册中心。
- `ToolRegistry` 支持：
  - `register(tool)` 注册工具。
  - `get(name)` 获取工具。
  - `list_tools()` 列出已注册工具。
  - `get_tool_schemas()` 导出工具 schema。
- 增加了最小校验：
  - 工具名重复时抛出明确错误。
  - 获取不存在的工具时抛出明确错误。
  - 工具运行结果统一使用 `ToolResult`。
- 在 `tests/test_tools.py` 中添加了注册中心相关测试。
- 当前阶段没有实现 calculator、search、todo 的具体业务逻辑，也没有实现 Runtime 或 LLM。
- 验证命令：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_tools.py
```

## 第 3 阶段：实现计算器工具

- 在 `tools/calculator.py` 中实现了 `CalculatorTool`。
- `CalculatorTool` 继承 `BaseTool`。
- 工具 schema 包含 `expression: string` 参数。
- 支持基础数学表达式：
  - 加法。
  - 减法。
  - 乘法。
  - 除法。
  - 括号。
  - 小数。
- 使用 `ast` 解析表达式，并限制可执行节点，避免使用不受控的 `eval`。
- 成功时通过 `ToolResult.data` 返回 `result`。
- 失败时通过 `ToolResult.error` 返回错误信息，例如除零错误和非法表达式。
- 在 `tests/test_tools.py` 中添加了计算器测试：
  - 正常表达式。
  - 小数表达式。
  - 除零错误。
  - 非法表达式。
- 当前阶段没有实现 search、todo，也没有实现 Runtime 自动调用工具。
- 验证命令：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_tools.py
```

## 第 4 阶段：实现 Mock 搜索工具

- 在 `tools/search.py` 中实现了 `MockSearchTool`。
- `MockSearchTool` 继承 `BaseTool`。
- 工具 schema 包含 `query: string` 参数。
- 内置了可控 mock 数据：
  - Python 是什么。
  - 北京天气。
  - 苹果手机价格。
  - Agent 工具注册中心。
- 搜索逻辑使用简单关键词匹配。
- 命中时返回 mock 结果列表。
- 未命中时返回空结果列表和友好提示。
- 返回内容明确说明结果来自 mock 数据，不是真实互联网搜索。
- 在 `tests/test_tools.py` 中添加了 Mock 搜索测试：
  - 命中结果。
  - 未命中结果。
  - 空 query 错误。
- 当前阶段没有接入真实网络搜索，没有实现 todo，也没有实现 Runtime 自动调用工具。
- 验证命令：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_tools.py
```

## 第 5 阶段：实现待办事项工具和会话内状态

- 在 `agent/session.py` 中实现了 `SessionState`。
- `SessionState` 包含：
  - `user_id`
  - `session_id`
  - `messages`
  - `todos`
  - `tool_traces`
- 在 `tools/todo.py` 中实现了 `TodoTool`。
- `TodoTool` 继承 `BaseTool`。
- `TodoTool` 支持以下操作：
  - `create` 创建待办。
  - `list` 查看待办。
  - `complete` 完成待办。
  - `delete` 删除待办。
- 每条 todo 至少包含：
  - `id`
  - `title`
  - `completed`
- `TodoTool` 通过传入的 `SessionState` 读写待办数据。
- 支持同一进程内不同 `user_id + session_id` 的会话隔离，避免待办事项互相污染。
- 在 `tests/test_tools.py` 中添加了待办工具测试：
  - 创建待办。
  - 查看待办。
  - 完成待办。
  - 删除待办。
  - 不同 session 隔离。
- 当前阶段没有实现落盘持久化，没有实现真实 LLM，也没有实现 Agent Runtime。
- 验证命令：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_tools.py
```

- 当前测试结果：`17 passed`。

## 第 6 阶段：实现 FakeLLM 和 JSON 决策协议

- 在 `agent/llm_client.py` 中定义了 `LLMClient` 抽象接口。
- `LLMClient` 提供 `complete(messages, tool_schemas)` 方法，用于返回 Agent 可解析的 JSON 决策字符串。
- 实现了 `FakeLLM`，用于本地测试：
  - 不调用真实 LLM API。
  - 支持传入预设响应列表。
  - 每次调用按顺序返回一个响应。
  - 支持预设响应为 JSON 字符串或 Python 字典。
  - 记录每次调用时传入的 `messages` 和 `tool_schemas`，方便后续 Runtime 测试断言。
- 实现了 `parse_llm_response` JSON 解析函数。
- JSON 决策协议只允许两种 action：
  - `tool`：表示调用工具。
  - `final`：表示最终回答。
- `tool` 决策要求包含：
  - `action`
  - `tool_name`
  - `arguments`
- `final` 决策要求包含：
  - `action`
  - `answer`
- 增加了明确错误处理：
  - 非法 JSON 会抛出明确错误。
  - 缺少 action 会抛出明确错误。
  - 非法 action 会抛出明确错误。
  - `tool` 决策缺少 `tool_name` 或 `arguments` 会抛出明确错误。
  - `final` 决策缺少 `answer` 会抛出明确错误。
- 在 `tests/test_runtime.py` 中新增了 FakeLLM 和 JSON 解析相关测试。
- 当前阶段没有接入真实 LLM API，没有实现 Agent Runtime，也没有让 Runtime 自动猜测工具。
- 验证命令：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_runtime.py
```

- 第 6 阶段测试结果：`10 passed`。
- 全量测试结果：`27 passed`。

## 第 7 阶段：实现最小 Agent Runtime Loop

- 在 `agent/runtime.py` 中实现了 `AgentRuntime`。
- `AgentRuntime` 支持以下输入：
  - `user_id`
  - `session_id`
  - `user_message`
- 实现了会话获取与创建逻辑：
  - 使用 `user_id + session_id` 作为会话隔离键。
  - 不存在会话时自动创建 `SessionState`。
  - 已存在会话时复用原有 `SessionState`。
- 实现了最小 Runtime 执行流程：
  - 记录用户消息到 `session.messages`。
  - 将当前会话消息和工具 schema 传给 `LLMClient`。
  - 使用 `parse_llm_response` 解析 LLM 返回的 JSON 决策。
  - 当 `action=tool` 时，从 `ToolRegistry` 获取工具并执行。
  - 当 `action=final` 时，记录 assistant 消息并返回自然语言答案。
- 实现了工具调用后的上下文记录：
  - 将工具结果写入 `session.messages`。
  - 将工具调用详情写入 `session.tool_traces`。
  - trace 中包含工具名、参数、成功状态、返回数据和错误信息。
- Runtime 调用工具时会把当前 `SessionState` 注入工具参数，支持 `TodoTool` 读写会话内待办数据。
- 增加了最大循环步数 `max_steps`：
  - 默认最大 5 步。
  - 超过最大步数时抛出明确错误，避免死循环。
- 增加了工具调用失败处理：
  - 工具不存在、工具执行异常或返回值不符合 `ToolResult` 时，会生成失败的 `ToolResult`。
  - 失败结果会作为工具结果写入上下文，允许 LLM 后续继续决策。
- 在 `tests/test_runtime.py` 中新增了 Runtime 测试：
  - 单步 final。
  - calculator 工具调用后 final。
  - mock_search 工具调用后 final。
  - todo create 工具调用后 final。
  - 超过最大 loop 步数时报错。
- 当前阶段继续使用 `FakeLLM` 测试。
- 当前阶段没有接入真实 LLM，没有把 Runtime 接入 CLI，也没有实现复杂摘要压缩。
- 验证命令：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_runtime.py
```

- 第 7 阶段 Runtime 测试结果：`15 passed`。
- 全量测试结果：`32 passed`。

## 第 8 阶段：把 Runtime 接入 CLI

- 在 `main.py` 中把 `AgentRuntime` 接入 CLI。
- CLI 启动时会创建以下对象：
  - `ToolRegistry`
  - `CalculatorTool`
  - `MockSearchTool`
  - `TodoTool`
  - `RuleBasedLLM`
  - `AgentRuntime`
- 新增了演示用 `RuleBasedLLM`：
  - 不调用真实 LLM API。
  - 用简单规则生成符合 JSON 决策协议的响应。
  - 用户输入计算表达式时调用 `calculator`。
  - 用户输入搜索请求时调用 `mock_search`。
  - 用户输入待办相关请求时调用 `todo`。
  - 其他输入直接返回 `final`。
- CLI 默认使用：
  - `user_id = local_user`
  - `session_id = default`
- CLI 支持输入 `exit` 或 `quit` 退出。
- 用户每次输入后，CLI 会打印 AgentRuntime 返回的自然语言回答。
- CLI 支持通过 Runtime 调用本地工具：
  - 计算器工具。
  - Mock 搜索工具。
  - 待办事项工具。
- 为了方便命令行演示，`RuleBasedLLM` 同时支持少量英文别名：
  - `search`
  - `add todo`
  - `list todo`
  - `complete`
  - `delete`
- 设置了 CLI 输出编码为 UTF-8，避免 Windows 管道演示时中文输出乱码。
- 更新了 `README.md`：
  - 当前阶段说明更新为第 8 阶段。
  - 增加 CLI 运行方式。
  - 增加 CLI 示例输入。
- 当前阶段没有接入真实 LLM API，没有实现真实 OpenAI-compatible API，也没有实现上下文摘要压缩。
- CLI 手动演示命令：

```powershell
@('calculate 1 + 2 * 3', 'search Python', 'add todo submit report', 'list todo', 'complete 1', 'quit') | .\.venv\Scripts\python.exe main.py
```

- CLI 手动演示结果：
  - 计算器返回：`计算结果是 7。`
  - Mock 搜索返回：找到 Python 相关 mock 结果。
  - 待办工具完成了创建、查看和完成操作。
- 全量测试命令：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

- 全量测试结果：`32 passed`。

## 第 9 阶段：实现受控上下文和摘要压缩

- 在 `agent/session.py` 中扩展了 `SessionState`。
- 新增了上下文控制字段：
  - `summary`
  - `max_messages`
- 新增了消息写入方法：
  - `add_message(message)`
  - 写入消息后会自动检查是否超过 `max_messages`。
- 新增了基础压缩方法：
  - `compress_messages()`
  - 当 `messages` 超过限制时，保留最近若干条消息。
  - 更早的消息会被压缩进 `summary`。
- 摘要生成使用简单规则，不调用真实 LLM：
  - 记录历史用户请求。
  - 记录工具调用结果。
  - 记录工具调用错误。
- 在 `agent/runtime.py` 中更新了 Runtime 上下文传递逻辑：
  - Runtime 通过 `SessionState.add_message()` 写入用户消息、工具消息和 assistant 消息。
  - 传给 `LLMClient` 的上下文包含 session summary。
  - 传给 `LLMClient` 的上下文包含最近消息。
  - 工具 schema 继续通过 `tool_schemas` 参数传入。
- 保持了 session 级别隔离：
  - 不同 `user_id + session_id` 拥有独立 `summary`。
  - 不同会话的摘要不会互相污染。
- 在 `tests/test_runtime.py` 中新增了受控上下文相关测试：
  - 超过 `max_messages` 后触发压缩。
  - Runtime 传给 LLM 的上下文包含 summary、最近消息和工具 schema。
  - 不同 session 的 summary 互相隔离。
  - 压缩后最近消息仍然保留。
- 更新了 `README.md`：
  - 当前阶段说明更新为第 9 阶段。
  - 说明项目已具备受控上下文压缩能力。
- 当前阶段没有实现复杂长期记忆，没有跨 session 共享记忆，也没有接入真实 LLM。
- 第 9 阶段 Runtime 测试命令：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_runtime.py
```

- 第 9 阶段 Runtime 测试结果：`19 passed`。
- 全量测试命令：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

- 全量测试结果：`36 passed`。
- CLI 简短演示命令：

```powershell
@('calculate 2 + 5', 'search Python', 'quit') | .\.venv\Scripts\python.exe main.py
```

- CLI 演示结果：
  - 计算器返回：`计算结果是 7。`
  - Mock 搜索返回：找到 Python 相关 mock 结果。

## 第 10 阶段：直接接入阿里云百炼 qwen3.7-plus

- 在 `agent/llm_client.py` 中实现了 `AliyunBailianLLM`。
- `AliyunBailianLLM` 使用 OpenAI Python SDK 的 OpenAI-compatible 调用方式。
- 百炼接入参数固定为：
  - `base_url = https://ws-sfjve45f4q20om2f.cn-beijing.maas.aliyuncs.com/compatible-mode/v1`
  - `model = qwen3.7-plus`
  - `extra_body = {"enable_thinking": True}`
  - `stream = True`
- 实现了 streaming 响应处理：
  - 只收集 `delta.content`。
  - 忽略 `delta.reasoning_content`。
  - 将所有 content 片段拼接为最终 JSON 字符串。
  - 不把 reasoning 内容交给 Runtime 的 JSON 解析器。
- system prompt 明确要求模型：
  - 只输出严格 JSON。
  - 不输出 Markdown。
  - 不输出额外解释。
  - 只能输出 `tool` 或 `final` 两种 action。
- Runtime 继续复用已有 JSON 协议：
  - `action=tool`
  - `action=final`
- 请求消息中包含：
  - system prompt。
  - 工具 schema 文本。
  - session summary。
  - 最近上下文消息。
  - 最近一次工具调用结果。
- 增加了真实 API 调用异常处理：
  - 网络或 SDK 调用异常会包装为明确错误。
  - 空响应会抛出明确错误。
  - 模型返回非法 JSON 会抛出明确错误。
- 在 `main.py` 中更新 CLI 启动逻辑：
  - 优先读取 `config/local_llm.json`。
  - 如果配置文件存在且包含 `api_key`，默认使用 `AliyunBailianLLM`。
  - 如果配置文件不存在或缺少 `api_key`，回退到 `RuleBasedLLM` 并打印清晰提示。
- 新增 `config/local_llm.example.json`：
  - 只包含示例占位值。
  - 不包含真实 API Key。
- 更新 `.gitignore`：
  - 已忽略 `config/local_llm.json`，避免真实 API Key 被提交。
- 更新 `requirements.txt`：
  - 增加 `openai` 依赖。
- 更新 `README.md`：
  - 增加阿里云百炼配置说明。
  - 增加 `config/local_llm.json` 创建方式。
  - 增加 CLI 启动说明。
- 在 `tests/test_runtime.py` 中新增测试：
  - 配置文件缺失时回退到 `RuleBasedLLM`。
  - 配置文件存在且包含 `api_key` 时选择 `AliyunBailianLLM`。
  - `AliyunBailianLLM` 能正确构造 `messages`、`model`、`extra_body` 和 `stream` 参数。
  - `AliyunBailianLLM` 能正确拼接 streaming content。
  - `AliyunBailianLLM` 会忽略 reasoning content。
  - 模型返回非法 JSON 时抛出明确错误。
- 测试中没有调用真实网络，全部使用 FakeLLM 或 mock OpenAI client。
- 本地已存在 `config/local_llm.json`，但未把其中真实 API Key 写入代码、README、record、测试或示例文件。
- 第 10 阶段测试命令：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

- 全量测试结果：`40 passed`。
- 真实 API 手动验证状态：
  - 尚未完成真实 API 手动验证。
  - 原因：当前虚拟环境缺少 `openai` SDK。
  - 已尝试通过 pip 安装 `openai`，但安装过程受网络/代理问题阻塞。
  - 已尝试启动 CLI，程序已优先选择百炼客户端，但因缺少 `openai` SDK 中止。
  - 需要先成功执行依赖安装后，才能用 `python main.py` 调用真实百炼 API。
- 依赖安装命令：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

- 百炼配置文件创建方式：

```powershell
copy config\local_llm.example.json config\local_llm.json
```

- 然后在 `config/local_llm.json` 中填写私密 `api_key`。

## 第 11 阶段：补齐端到端测试用例

- 新增 `tests/test_e2e.py`，专门放置端到端测试用例。
- 端到端测试继续使用 `FakeLLM` 精确控制每一步 action。
- 测试中没有调用真实 LLM。
- 测试中没有调用真实网络。
- 没有为了测试硬编码 Runtime 行为。
- 新增了 10 个端到端测试场景：
  - 用户直接闲聊，Agent 不调用工具，直接返回 final。
  - 用户要求计算 `128 * 36 + 450`，Agent 调用 `calculator` 并返回结果。
  - 用户搜索 `Python 是什么`，Agent 调用 `mock_search` 并总结结果。
  - 用户添加待办 `明天下午三点提交周报`，Agent 调用 `todo create`。
  - 用户查看当前待办，Agent 调用 `todo list`。
  - 用户把 `提交周报` 标记完成，Agent 调用 `todo complete`。
  - 用户搜索苹果手机模拟价格，并计算买 3 台多少钱，Agent 先调用 `mock_search` 再调用 `calculator`。
  - 用户搜索北京天气，如果下雨就添加 `带伞` 待办，Agent 先调用 `mock_search` 再调用 `todo create`。
  - 用户计算午饭 32、打车 48、咖啡 26 的总额，并记录 `报销今天开销` 待办，Agent 先调用 `calculator` 再调用 `todo create`。
  - 用户删除刚才的报销待办，Agent 调用 `todo delete`。
- 每个端到端测试都断言了最终自然语言回答。
- 涉及工具调用的测试都断言了 `session.tool_traces`。
- 涉及待办事项的测试都断言了 `session.todos` 状态变化。
- 在添加待办和删除待办场景中验证了 session 隔离仍然有效。
- 更新了 `README.md`：
  - 当前阶段说明更新为第 11 阶段。
  - 测试命令更新为运行全量测试。
- 第 11 阶段端到端测试命令：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_e2e.py
```

- 第 11 阶段端到端测试结果：`10 passed`。
- 全量测试命令：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

- 全量测试结果：`50 passed`。

## 第 12 阶段：最后整理和演示文档

- 对项目结构进行了最后检查。
- 当前项目保留的核心目录和文件包括：
  - `main.py`
  - `agent/`
  - `tools/`
  - `tests/`
  - `config/local_llm.example.json`
  - `requirements.txt`
  - `README.md`
  - `record.md`
- 没有引入新的 Agent 框架。
- 没有进行大规模重构。
- 没有改变核心功能边界。
- 改进了 CLI 启动时的异常友好性：
  - 当存在 `config/local_llm.json` 但百炼客户端初始化失败时，会打印清晰提示。
  - 会回退到 `RuleBasedLLM` 演示模式，避免 CLI 直接崩溃。
  - 提示用户确认是否安装了 `requirements.txt` 中的 `openai` 依赖。
- 整理并重写了 `README.md`，包含：
  - 项目简介。
  - 架构说明。
  - 工具列表。
  - Agent Runtime 流程。
  - 如何运行 CLI。
  - 如何配置阿里云百炼 qwen3.7-plus。
  - 示例对话。
  - 如何运行测试。
- README 中明确说明：
  - `config/local_llm.json` 用于保存本地私密 API Key。
  - `config/local_llm.json` 已被 `.gitignore` 忽略。
  - 不要提交真实 API Key。
  - 测试不会调用真实 LLM，也不会访问真实网络。
- 更新了 `tests/test_runtime.py`：
  - 增加百炼客户端初始化失败时回退到 `RuleBasedLLM` 的测试。
- 当前虚拟环境已可导入 `openai` SDK：
  - `openai` 版本为 `2.44.0`。
- 最终全量测试命令：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

- 最终全量测试结果：`51 passed`。
- CLI 简短演示命令：

```powershell
@('calculate 1 + 2 * 3', 'search Python', 'quit') | .\.venv\Scripts\python.exe main.py
```

- CLI 简短演示结果：
  - 成功启动 CLI。
  - 成功处理计算请求，返回 `计算结果是 7。`
  - 成功处理搜索请求，返回 Python 相关回答。
  - 成功输入 `quit` 退出。
- 本阶段最终状态：
  - 项目已经成为一个清晰的最小可用 Agent Demo。
  - 本地工具、Runtime、上下文压缩、CLI、百炼接入和端到端测试均已具备。

## 第 12 阶段：为当前 Agent 增加真实联网搜索能力

- 在 `tools/search.py` 中新增了 `WebSearchTool`。
- `WebSearchTool` 继承 `BaseTool`，工具名为 `web_search`。
- `web_search` 的工具 schema 包含：
  - `query`
  - 类型为字符串。
  - 用于接收真实联网搜索关键词。
- 实现了真实联网搜索流程：
  - 首先访问 DuckDuckGo HTML 搜索页面。
  - 解析搜索结果标题、链接、摘要和来源。
  - 当 HTML 页面没有解析出结果时，自动使用 DuckDuckGo Instant Answer JSON 接口作为兜底。
  - 不需要额外搜索 API Key。
- 增加了搜索结果链接处理：
  - 支持解析 DuckDuckGo 跳转链接中的真实目标地址。
  - 普通链接会原样返回。
- 增加了友好错误处理：
  - 空 query 会返回明确错误。
  - 网络不可用、超时或请求失败时，会返回 `Real web search failed: ...`。
  - HTML 搜索无结果且 JSON 兜底也无结果时，会返回空结果和明确提示。
- 保留了原有 `MockSearchTool`：
  - 旧的 mock 搜索测试和离线演示能力没有被删除。
  - 端到端测试中原有 mock 搜索场景继续可用。
- 在 `main.py` 中更新 CLI 装配：
  - 启动 Runtime 时注册 `WebSearchTool`。
  - 同时继续注册 `MockSearchTool`。
  - 规则演示模式下，用户输入 `搜索 ...` 或 `search ...` 会优先调用 `web_search`。
- 更新了搜索结果格式化：
  - `web_search` 返回时显示为真实联网搜索结果。
  - `mock_search` 返回时仍显示为 mock 搜索结果。
- 在 `tests/test_tools.py` 中新增真实搜索工具测试：
  - 解析 DuckDuckGo HTML 搜索结果。
  - HTML 无结果时使用 Instant Answer JSON 兜底。
  - HTML 和 JSON 都无结果时返回空结果。
  - 空 query 返回错误。
  - 网络请求失败时返回友好错误。
- 在 `tests/test_runtime.py` 中新增 Runtime/CLI 装配测试：
  - Runtime 可以调用 `web_search` 工具。
  - `RuleBasedLLM` 会把搜索请求路由到 `web_search`。
  - `main.build_runtime()` 会注册 `web_search` 和 `mock_search`。
- 更新了 `README.md`：
  - 工具列表中增加 `web_search`。
  - 说明真实联网搜索基于 DuckDuckGo。
  - 说明测试不会访问真实网络，真实搜索能力通过假 HTML/JSON 进行自动化测试。
- 当前阶段没有实现浏览器渲染、爬取正文、搜索结果排序、缓存、代理配置或多搜索引擎聚合。
- 针对搜索和 Runtime 的测试命令：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_tools.py tests/test_runtime.py
```

- 针对搜索和 Runtime 的测试结果：`49 passed`。
- 全量测试命令：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

- 全量测试结果：`59 passed`。
- 真实联网手动验证命令：

```powershell
.\.venv\Scripts\python.exe -c "from tools.search import WebSearchTool; r=WebSearchTool(timeout=10, max_results=2).run({'query': 'Python'}); print(r.success); print(r.error); print(r.data)"
```

- 真实联网手动验证结果：
  - `success=True`
  - `error=None`
  - 成功返回 DuckDuckGo 的真实搜索结果。
  - 命令环境打印了一段 Conda PATH 解析警告，但不影响 `WebSearchTool` 执行结果。

## 第 13 阶段：最后整理和演示文档

- 根据当前最终项目状态整理了收尾文档。
- 更新了 `README.md`，使其覆盖当前最小可用 Agent Demo 的完整内容：
  - 项目简介。
  - 当前已具备的能力列表。
  - 项目目录结构。
  - 核心模块说明。
  - 工具列表。
  - Agent Runtime 流程。
  - CLI 运行方式。
  - 阿里云百炼 qwen3.7-plus 配置方式。
  - 示例对话。
  - 简短演示命令。
  - 测试运行方式。
  - 常见问题排查。
- 在 README 中补充了真实联网搜索说明：
  - `web_search` 使用 DuckDuckGo HTML 搜索。
  - HTML 无结果时会使用 DuckDuckGo Instant Answer JSON 兜底。
  - 测试不会访问真实网络，而是通过假 HTML/JSON 验证解析逻辑。
- 在 README 中补充了 CLI 使用说明：
  - 没有 `config/local_llm.json` 时会回退到 `RuleBasedLLM` 演示模式。
  - 存在 `config/local_llm.json` 且包含 `api_key` 时，会优先使用阿里云百炼。
  - 搜索请求需要本机可访问外网。
- 在 README 中补充了常见错误说明：
  - 百炼连接失败时检查网络、代理、API Key 和服务地址。
  - LLM 返回非法 JSON 时检查严格 JSON 协议。
  - 搜索无结果时说明可能与 DuckDuckGo 返回内容和网络环境有关。
- 在 `main.py` 中增加了 `format_agent_error()`：
  - 对阿里云百炼请求失败给出更友好的中文提示。
  - 对 LLM 返回非法 JSON 给出更明确说明。
  - 对 Runtime 超过最大循环步数给出防止死循环的提示。
  - 其他异常仍保留原始错误信息，方便定位。
- 在 `tests/test_runtime.py` 中补充了异常提示测试：
  - 百炼请求失败提示。
  - 非法 JSON 提示。
  - 最大循环步数超限提示。
- 本阶段没有引入新框架。
- 本阶段没有改变核心功能边界。
- 本阶段没有提前实现后续阶段内容。
- 全量测试命令：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

- 全量测试结果：`62 passed`。
- CLI 简短手动演示命令：

```powershell
@('calculate 1 + 2 * 3', 'quit') | .\.venv\Scripts\python.exe main.py
```

- CLI 简短手动演示结果：
  - 成功启动 CLI。
  - 成功加载本地 `config/local_llm.json`，使用阿里云百炼 qwen3.7-plus。
  - 输入 `calculate 1 + 2 * 3` 后返回 `7`。
  - 输入 `quit` 后正常退出。
- 当前最终项目状态：
  - 项目已经具备本地 Agent Runtime、工具注册、计算器、mock 搜索、真实联网搜索、待办事项、会话状态、上下文压缩、百炼接入、CLI、端到端测试和完整演示文档。
