# 最小可用 Agent 分阶段开发 Prompt

下面这些 prompt 是按阶段发送给 Codex 的。不要一次性把所有 prompt 都发给 Codex；每完成一个阶段并确认测试通过后，再发送下一阶段。

## 总目标说明

我要从零实现一个最小可用版本的本地 Agent。这个 Agent 需要在独立、记忆受控的会话环境中，接收用户输入，自主决策并驱动本地工具完成任务，最后把结果转化为自然语言反馈给用户。

工具包括：

- 计算器工具
- Mock 搜索工具
- 待办事项工具
- 工具注册中心
- 工具基类

限制：

- 不使用 LangGraph、OpenHands、OpenClaw 等 Agent 框架。
- 使用 Python 实现。
- 优先保证最小可用、结构清晰、易于测试和演示。
- 每个阶段只实现当前阶段要求，不要提前生成后续阶段的大量代码。

推荐目录结构：

```text
main.py
agent/
  __init__.py
  runtime.py
  session.py
  llm_client.py
tools/
  __init__.py
  registry.py
  calculator.py
  search.py
  todo.py
tests/
  __init__.py
  test_tools.py
  test_runtime.py
requirements.txt
README.md
```

---

## 第 1 阶段 Prompt：建立项目骨架和最小运行入口

```text
请你只完成第 1 阶段：为一个最小可用本地 Agent 建立 Python 项目骨架。

目标：
1. 创建必要目录和空模块：
   - main.py
   - agent/__init__.py
   - agent/runtime.py
   - agent/session.py
   - agent/llm_client.py
   - tools/__init__.py
   - tools/registry.py
   - tools/calculator.py
   - tools/search.py
   - tools/todo.py
   - tests/__init__.py
   - tests/test_tools.py
   - tests/test_runtime.py
2. 在 main.py 中实现一个最小 CLI 循环：
   - 启动后提示用户输入
   - 用户输入 exit 或 quit 时退出
   - 暂时只把用户输入回显出来
3. requirements.txt 中只加入当前阶段需要的最少依赖。
4. README.md 中写清楚项目目标、目录结构、如何运行。

约束：
- 不要实现 Agent Runtime。
- 不要实现工具逻辑。
- 不要接入真实 LLM。
- 保持代码最小、清晰、可运行。

完成后请运行基础检查，确认 `python main.py` 能启动。
```

---

## 第 2 阶段 Prompt：实现工具基类和工具注册中心

```text
请你只完成第 2 阶段：实现工具基类和工具注册中心。

目标：
1. 在 tools/registry.py 中实现：
   - BaseTool 基类
   - ToolResult 数据结构
   - ToolRegistry 注册中心
2. 每个工具至少包含：
   - name
   - description
   - parameters JSON Schema
   - run(arguments: dict) 方法
3. ToolRegistry 需要支持：
   - register(tool)
   - get(name)
   - list_tools()
   - get_tool_schemas()
4. 添加最小参数校验：
   - 工具名重复时抛出明确错误
   - 调用不存在工具时抛出明确错误
   - 工具 run 统一返回 ToolResult
5. 在 tests/test_tools.py 中添加注册中心相关测试。

约束：
- 不要实现 calculator/search/todo 的具体业务逻辑。
- 不要实现 Agent Runtime。
- 不要接入 LLM。
- 测试必须使用 pytest。

完成后请运行 `pytest tests/test_tools.py`。
```

---

## 第 3 阶段 Prompt：实现计算器工具

```text
请你只完成第 3 阶段：实现计算器工具。

目标：
1. 在 tools/calculator.py 中实现 CalculatorTool。
2. CalculatorTool 需要继承 BaseTool。
3. 工具 schema 至少包含：
   - expression: string
4. 支持基本数学表达式：
   - 加、减、乘、除
   - 括号
   - 小数
5. 必须安全计算表达式：
   - 不允许直接使用不受控的 eval
   - 可以使用 ast 解析并限制节点类型
6. 返回 ToolResult：
   - 成功时包含 result
   - 失败时包含 error
7. 在 tests/test_tools.py 中增加计算器测试：
   - 正常表达式
   - 小数
   - 除零错误
   - 非法表达式

约束：
- 不要实现 search/todo。
- 不要实现 Runtime 自动调用工具。
- 保持实现最小但安全。

完成后请运行 `pytest tests/test_tools.py`。
```

---

## 第 4 阶段 Prompt：实现 Mock 搜索工具

```text
请你只完成第 4 阶段：实现 Mock 搜索工具。

目标：
1. 在 tools/search.py 中实现 MockSearchTool。
2. MockSearchTool 需要继承 BaseTool。
3. 工具 schema 至少包含：
   - query: string
4. 内置一份可控的 mock 数据，例如：
   - Python 是什么
   - 北京天气
   - 苹果手机价格
   - Agent 工具注册中心
5. 搜索行为：
   - 根据 query 做简单关键词匹配
   - 命中时返回结果列表
   - 未命中时返回空结果和友好提示
6. 返回内容必须明确这是 mock 搜索结果，不是真实互联网结果。
7. 在 tests/test_tools.py 中增加 Mock 搜索测试：
   - 命中结果
   - 未命中结果
   - 空 query 错误

约束：
- 不要接入真实网络搜索。
- 不要实现 todo。
- 不要实现 Runtime 自动调用工具。

完成后请运行 `pytest tests/test_tools.py`。
```

---

## 第 5 阶段 Prompt：实现待办事项工具和会话内状态

```text
请你只完成第 5 阶段：实现待办事项工具和基础会话状态。

目标：
1. 在 agent/session.py 中实现 SessionState：
   - user_id
   - session_id
   - messages
   - todos
   - tool_traces
2. 支持同一进程内的会话隔离：
   - 不同 user_id + session_id 的 todos 不能互相污染
3. 在 tools/todo.py 中实现 TodoTool。
4. TodoTool 需要继承 BaseTool。
5. TodoTool 的操作至少支持：
   - create
   - list
   - complete
   - delete
6. 每条 todo 至少包含：
   - id
   - title
   - completed
7. TodoTool 必须通过传入的 SessionState 读写 todos。
8. 在 tests/test_tools.py 中增加待办工具测试：
   - 创建待办
   - 查看待办
   - 完成待办
   - 删除待办
   - 不同 session 隔离

约束：
- 暂时不需要落盘持久化。
- 暂时只做会话内状态持久化。
- 不要实现真实 LLM。

完成后请运行 `pytest tests/test_tools.py`。
```

---

## 第 6 阶段 Prompt：实现 FakeLLM 和 JSON 决策协议

```text
请你只完成第 6 阶段：实现 FakeLLM 和 Agent 决策协议。

目标：
1. 在 agent/llm_client.py 中定义 LLMClient 抽象接口。
2. 实现 FakeLLM，用于测试，不调用真实 API。
3. Agent 和 LLM 之间使用严格 JSON 协议。
4. LLM 输出只允许两种 action：

   调用工具：
   {
     "action": "tool",
     "tool_name": "calculator",
     "arguments": {
       "expression": "1 + 2"
     }
   }

   最终回答：
   {
     "action": "final",
     "answer": "计算结果是 3。"
   }

5. FakeLLM 支持按顺序返回预设响应，方便 Runtime 测试。
6. 增加 JSON 解析函数：
   - 合法 JSON 正常解析
   - 非法 JSON 返回明确错误
   - action 缺失或非法时返回明确错误

约束：
- 不要接入真实 LLM API。
- 不要写复杂 prompt。
- 不要让 Runtime 自己猜工具，工具选择由 LLM JSON 决策表达。

完成后请新增或更新 tests/test_runtime.py，覆盖 FakeLLM 和 JSON 解析。
运行 `pytest tests/test_runtime.py`。
```

---

## 第 7 阶段 Prompt：实现最小 Agent Runtime Loop

```text
请你只完成第 7 阶段：实现最小 Agent Runtime Loop。

目标：
1. 在 agent/runtime.py 中实现 AgentRuntime。
2. Runtime 输入：
   - user_id
   - session_id
   - user_message
3. Runtime 流程：
   - 获取或创建 SessionState
   - 记录用户消息
   - 把用户消息、会话上下文、工具 schema 传给 LLMClient
   - 解析 LLM 返回的 JSON
   - 如果 action=tool：
     - 从 ToolRegistry 获取工具
     - 执行工具
     - 记录 tool trace
     - 把工具结果加入上下文
     - 继续 loop
   - 如果 action=final：
     - 记录 assistant 消息
     - 返回自然语言 answer
4. 设置最大 loop 步数，例如 5 步，避免死循环。
5. 工具调用失败时：
   - 将错误作为工具结果反馈给 LLM
   - 允许 LLM 再决定 final 或下一步
6. 在 tests/test_runtime.py 中增加测试：
   - 单步 final
   - calculator 工具调用后 final
   - search 工具调用后 final
   - todo create 后 final
   - 超过最大 loop 步数时报错

约束：
- 继续使用 FakeLLM 测试。
- 不要接入真实 LLM。
- 不要实现复杂摘要压缩。

完成后请运行全部测试：`pytest`。
```

---

## 第 8 阶段 Prompt：把 Runtime 接入 CLI

```text
请你只完成第 8 阶段：把 AgentRuntime 接入 main.py 的 CLI。

目标：
1. main.py 启动时创建：
   - ToolRegistry
   - CalculatorTool
   - MockSearchTool
   - TodoTool
   - LLMClient
   - AgentRuntime
2. 为了当前阶段可演示，允许 main.py 使用一个简单 RuleBasedLLM 或 FakeLLM 变体：
   - 用户说“计算”或包含数学表达式时调用 calculator
   - 用户说“搜索”时调用 mock_search
   - 用户说“待办/添加/完成/删除/查看”时调用 todo
   - 其他输入直接 final
3. CLI 支持：
   - 默认 user_id 为 local_user
   - 默认 session_id 为 default
   - exit/quit 退出
4. 用户每次输入后，打印 Agent 的自然语言回答。
5. README.md 增加 CLI 演示用法。

约束：
- 这个阶段仍然不接真实 LLM。
- RuleBasedLLM 只用于最小演示，不要写得过度复杂。
- 保持代码结构便于下一阶段替换真实 LLM。

完成后请手动运行 `python main.py` 做一次简单演示，并运行 `pytest`。
```

---

## 第 9 阶段 Prompt：实现受控上下文和摘要压缩

```text
请你只完成第 9 阶段：实现受控上下文和基础摘要压缩。

目标：
1. 在 SessionState 中增加上下文轮次限制，例如 max_messages。
2. 当 messages 超过限制时，进行基础压缩：
   - 保留最近若干条消息
   - 将更早的消息压缩成 summary 字段
3. summary 可以先使用简单规则生成，不需要调用真实 LLM，例如：
   - 记录历史中出现过的关键用户请求
   - 记录已完成的重要工具结果
4. Runtime 给 LLM 的上下文应包含：
   - summary
   - 最近消息
   - 工具 schema
5. 增加测试：
   - 超过 max_messages 后触发压缩
   - 不同 session 的 summary 互相隔离
   - 压缩后最近消息仍保留

约束：
- 不要实现复杂长期记忆。
- 不要跨 session 共享记忆。
- 不要接真实 LLM。

完成后请运行 `pytest`。
```

---

## 第 10 阶段 Prompt：直接接入阿里云百炼 qwen3.7-plus

```text
请你只完成第 10 阶段：把当前 Agent 从 RuleBasedLLM/FakeLLM 演示模式升级为可以直接调用阿里云百炼平台 qwen3.7-plus 模型的版本。

这一阶段的重点是：CLI 默认应优先使用真实 LLM 来决策是否调用工具，并通过真实 LLM 完成多步 tool loop。FakeLLM 只保留给测试使用，RuleBasedLLM 只作为没有配置 API 时的兜底方案。

目标：
1. 在 agent/llm_client.py 中实现 DashScopeLLM 或 AliyunBailianLLM。
2. 使用 `openai` Python SDK，而不是直接使用 httpx。
3. requirements.txt 增加 `openai` 依赖。
4. 按阿里云百炼 OpenAI-compatible 调用方式创建 client：

   ```python
   from openai import OpenAI

   client = OpenAI(
       api_key=api_key,
       base_url="https://ws-sfjve45f4q20om2f.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
   )
   ```

5. 模型固定使用：

   ```python
   model="qwen3.7-plus"
   ```

6. 不要使用环境变量读取 API Key。请改为读取本地私密配置文件，例如：

   ```text
   config/local_llm.json
   ```

   配置文件格式：

   ```json
   {
     "api_key": "在这里填写你的阿里云百炼 API Key"
   }
   ```

7. 必须新增 `config/local_llm.example.json`，只放示例占位值，不要放真实 API Key。
8. 必须确保 `config/local_llm.json` 被 `.gitignore` 忽略，避免真实 API Key 被提交。
9. main.py / CLI 启动时：
   - 如果 `config/local_llm.json` 存在且包含 `api_key`，则默认使用 DashScopeLLM/AliyunBailianLLM
   - 如果配置文件不存在或缺少 api_key，再回退到 RuleBasedLLM，并向用户打印清晰提示
10. 请求中必须包含：
   - system prompt
   - 当前用户消息
   - session summary
   - 最近上下文
   - tools schema 文本或等价的工具说明
   - 最近一次工具调用结果，如果当前 loop 中已有工具结果
11. 调用模型时参考以下参数：

   ```python
   completion = client.chat.completions.create(
       model="qwen3.7-plus",
       messages=messages,
       extra_body={"enable_thinking": True},
       stream=True,
   )
   ```

12. 因为当前 Agent Runtime 需要解析严格 JSON：
   - 如果使用 stream=True，必须只收集 `delta.content` 拼接为最终内容
   - 可以忽略或不打印 `delta.reasoning_content`
   - 不要把 reasoning_content 放进 Runtime 的 JSON 解析器
   - 最终只解析完整的 content 字符串
13. system prompt 必须明确要求模型最终 content 只输出 JSON，不要输出 Markdown，不要输出额外解释。
14. LLM 输出只允许两种 JSON：

   调用工具：
   {
     "action": "tool",
     "tool_name": "calculator",
     "arguments": {
       "expression": "1 + 2"
     }
   }

   最终回答：
   {
     "action": "final",
     "answer": "计算结果是 3。"
   }

15. Runtime 必须继续复用已有 JSON 解析和工具调用 loop：
   - action=tool
   - action=final
16. 增加真实 API 调用的异常处理：
   - 网络错误
   - 超时
   - 401/403 鉴权错误
   - 非 2xx 响应
   - 响应 JSON 结构不符合预期
   - 模型返回非法 JSON
17. README.md 增加阿里云百炼配置说明和启动示例。
18. 测试中不要调用真实 API：
   - 使用 mock OpenAI client 或 FakeLLM
   - 确保配置文件缺失时行为明确
   - 确保配置文件存在时 CLI 会选择 DashScopeLLM/AliyunBailianLLM
   - 确保 DashScopeLLM/AliyunBailianLLM 能正确构造 messages、model、extra_body 并解析 streaming 响应
19. 如果当前本地已经创建 `config/local_llm.json` 并填入 API Key，请在完成单元测试后做一次最小手动验证：
   - 启动 `python main.py`
   - 输入一个简单问题，例如“你好”
   - 输入一个需要工具的问题，例如“帮我计算 128 * 36 + 450”
   - 观察真实 LLM 是否能输出 JSON 并驱动工具
   如果当前本地没有配置文件或没有 API Key，请不要编造验证结果，只说明缺少 `config/local_llm.json` 或 `api_key`。

约束：
- CLI 运行时要真正调用 API，不要继续默认使用 FakeLLM。
- 测试里不要访问真实网络。
- 不要把 API Key 写入代码。
- 不要把 API Key 写入 prompt_records.md、README.md、测试文件、示例文件或任何会提交的文件。
- 保持 FakeLLM 测试继续可用。
- 不要引入 LangGraph、OpenHands、OpenClaw 等 Agent 框架。
- 不要把真实 LLM 的返回当作自然语言直接展示，必须先按既有 JSON 协议解析。

完成后请运行 `pytest`，并说明：
1. 修改了哪些文件。
2. 如何创建 `config/local_llm.json`。
3. 如何用阿里云百炼 qwen3.7-plus 启动 CLI。
4. 是否完成了真实 API 手动验证；如果没有，缺少什么配置。
```

---

## 第 11 阶段 Prompt：补齐端到端测试用例

```text
请你只完成第 11 阶段：补齐最小可用 Agent 的端到端测试。

目标：
请在 tests/test_runtime.py 或新增测试文件中覆盖以下 10 个测试用例：

1. 用户直接闲聊，Agent 不调用工具，直接 final。
2. 用户要求计算 `128 * 36 + 450`，Agent 调用 calculator 并返回结果。
3. 用户搜索 `Python 是什么`，Agent 调用 mock_search 并总结结果。
4. 用户添加待办 `明天下午三点提交周报`，Agent 调用 todo create。
5. 用户查看当前待办，Agent 调用 todo list。
6. 用户把 `提交周报` 标记完成，Agent 调用 todo complete。
7. 用户搜索苹果手机模拟价格，并计算买 3 台多少钱，Agent 先 search 再 calculator。
8. 用户搜索北京天气，如果下雨就添加 `带伞` 待办，Agent 先 search 再 todo create。
9. 用户计算午饭 32、打车 48、咖啡 26 的总额，并记录 `报销今天开销` 待办，Agent 先 calculator 再 todo create。
10. 用户删除刚才的报销待办，Agent 调用 todo delete。

要求：
- 使用 FakeLLM 精确控制每一步 action。
- 断言工具调用 trace。
- 断言最终自然语言回答。
- 断言 todo 状态变化。
- 断言 session 隔离仍然有效。

约束：
- 不要调用真实 LLM。
- 不要调用真实网络。
- 不要为了测试硬编码 Runtime 行为。

完成后请运行 `pytest`。
```

---
## 第 12 阶段 Prompt：为当前 Agent 增加真实联网搜索能力
请你为当前 Agent 增加真实联网搜索能力。

目标：
1. 保留 MockSearchTool，但新增 WebSearchTool。
2. WebSearchTool 放在 tools/search.py 中，继承 BaseTool。
3. WebSearchTool 的 name 使用 "search"，description 明确说明这是联网搜索工具。
4. WebSearchTool 支持参数：
   - query: string
   - max_results: integer，可选，默认 5
5. 使用一个真实搜索 API 实现联网搜索，优先选择 Serper、Tavily、Bing、Brave Search 中实现最简单的一种。
6. 不要把搜索 API Key 写进代码。
7. 不使用环境变量，改为读取本地私密配置文件：
   config/local_search.json
8. 新增 config/local_search.example.json，示例格式如下：
   {
     "provider": "serper",
     "api_key": "在这里填写你的搜索 API Key"
   }
9. 确保 config/local_search.json 加入 .gitignore。
10. main.py 中注册 WebSearchTool，让 Agent 默认使用真实 search 工具。
11. 如果 config/local_search.json 不存在，则回退到 MockSearchTool，并打印清晰提示。
12. README.md 增加联网搜索配置说明。
13. 测试中不要真实访问网络，使用 mock HTTP response 测试 WebSearchTool。

约束：
- 不要删除 FakeLLM 测试。
- 不要把任何 API Key 写入 README、测试文件或示例文件。
- Runtime 仍然必须通过 JSON tool loop 调用搜索工具。


## 第 13 阶段 Prompt：最后整理和演示文档

```text
请你只完成第 13 阶段：整理项目，使它成为一个清晰的最小可用 Agent Demo。

目标：
1. 检查代码结构，删除无用代码和重复逻辑。
2. 确保 README.md 包含：
   - 项目简介
   - 架构说明
   - 工具列表
   - Agent Runtime 流程
   - 如何运行 CLI
   - 如何运行测试
   - 如何配置真实 OpenAI-compatible API
   - 示例对话
3. 确保异常信息对用户友好。
4. 确保所有测试通过。
5. 给出最终项目状态总结。

约束：
- 不要大规模重构。
- 不要引入新框架。
- 不要改变核心功能边界。
- 只做最小可用版本的收尾整理。

完成后请运行：
- `pytest`
- `python main.py` 的简短手动演示
```
