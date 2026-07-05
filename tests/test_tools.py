import pytest

from agent.session import SessionState
from tools.calculator import CalculatorTool
from tools.registry import BaseTool, ToolRegistry, ToolResult
from tools.search import MockSearchTool, WebSearchTool
from tools.todo import TodoTool


class DummyTool(BaseTool):
    name = "dummy"
    description = "A test-only tool."
    parameters = {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
        },
        "required": ["text"],
    }

    def run(self, arguments: dict) -> ToolResult:
        return ToolResult(success=True, data={"echo": arguments["text"]})


def test_registry_registers_and_gets_tool() -> None:
    registry = ToolRegistry()
    tool = DummyTool()

    registry.register(tool)

    assert registry.get("dummy") is tool
    assert registry.list_tools() == [tool]


def test_registry_rejects_duplicate_tool_names() -> None:
    registry = ToolRegistry()
    registry.register(DummyTool())

    with pytest.raises(ValueError, match="already registered"):
        registry.register(DummyTool())


def test_registry_raises_for_missing_tool() -> None:
    registry = ToolRegistry()

    with pytest.raises(KeyError, match="not registered"):
        registry.get("missing")


def test_registry_returns_tool_schemas() -> None:
    registry = ToolRegistry()
    registry.register(DummyTool())

    assert registry.get_tool_schemas() == [
        {
            "name": "dummy",
            "description": "A test-only tool.",
            "parameters": DummyTool.parameters,
        }
    ]


def test_tool_run_returns_tool_result() -> None:
    result = DummyTool().run({"text": "hello"})

    assert isinstance(result, ToolResult)
    assert result.success is True
    assert result.data == {"echo": "hello"}
    assert result.error is None


def test_calculator_evaluates_basic_expression() -> None:
    result = CalculatorTool().run({"expression": "1 + 2 * (3 + 4)"})

    assert result.success is True
    assert result.data["result"] == 15
    assert result.error is None


def test_calculator_evaluates_decimal_expression() -> None:
    result = CalculatorTool().run({"expression": "1.5 + 2.25"})

    assert result.success is True
    assert result.data["result"] == 3.75


def test_calculator_returns_error_for_division_by_zero() -> None:
    result = CalculatorTool().run({"expression": "10 / 0"})

    assert result.success is False
    assert result.data == {}
    assert result.error == "Division by zero is not allowed."


def test_calculator_returns_error_for_invalid_expression() -> None:
    result = CalculatorTool().run({"expression": "__import__('os').system('echo unsafe')"})

    assert result.success is False
    assert result.data == {}
    assert "Invalid expression" in result.error


def test_mock_search_returns_matching_results() -> None:
    result = MockSearchTool().run({"query": "Python 是什么"})

    assert result.success is True
    assert result.error is None
    assert result.data["results"]
    assert result.data["results"][0]["source"] == "mock"
    assert "Mock search results" in result.data["message"]


def test_mock_search_returns_empty_results_for_no_match() -> None:
    result = MockSearchTool().run({"query": "不存在的关键词"})

    assert result.success is True
    assert result.error is None
    assert result.data["results"] == []
    assert "not a real internet search" in result.data["message"]


def test_mock_search_returns_error_for_empty_query() -> None:
    result = MockSearchTool().run({"query": "   "})

    assert result.success is False
    assert result.data == {}
    assert result.error == "Query must be a non-empty string."


def test_web_search_parses_duckduckgo_html_results() -> None:
    captured = {}

    def fake_fetcher(url: str, timeout: float) -> str:
        captured["url"] = url
        captured["timeout"] = timeout
        return """
        <html>
          <body>
            <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.python.org%2F">
              Python
            </a>
            <a class="result__snippet">Python is a programming language.</a>
            <a class="result__a" href="https://docs.python.org/3/">
              Python Docs
            </a>
            <div class="result__snippet">Official Python documentation.</div>
          </body>
        </html>
        """

    result = WebSearchTool(timeout=3.0, max_results=2, html_fetcher=fake_fetcher).run({"query": "Python"})

    assert result.success is True
    assert result.error is None
    assert captured["url"].endswith("?q=Python")
    assert captured["timeout"] == 3.0
    assert result.data["query"] == "Python"
    assert result.data["message"] == "Real web search results from DuckDuckGo."
    assert result.data["results"] == [
        {
            "title": "Python",
            "url": "https://www.python.org/",
            "snippet": "Python is a programming language.",
            "source": "duckduckgo",
        },
        {
            "title": "Python Docs",
            "url": "https://docs.python.org/3/",
            "snippet": "Official Python documentation.",
            "source": "duckduckgo",
        },
    ]


def test_web_search_uses_instant_answer_fallback_when_html_has_no_results() -> None:
    requested_urls = []

    def fake_fetcher(url: str, timeout: float) -> str:
        requested_urls.append(url)
        if "api.duckduckgo.com" in url:
            return """
            {
              "Heading": "Python",
              "AbstractText": "Python is a high-level programming language.",
              "AbstractURL": "https://www.python.org/",
              "RelatedTopics": [
                {
                  "Text": "Python Package Index - The official third-party software repository for Python.",
                  "FirstURL": "https://pypi.org/"
                }
              ]
            }
            """

        return "<html></html>"

    result = WebSearchTool(max_results=2, html_fetcher=fake_fetcher).run({"query": "Python"})

    assert result.success is True
    assert len(requested_urls) == 2
    assert "duckduckgo.com/html/" in requested_urls[0]
    assert "api.duckduckgo.com" in requested_urls[1]
    assert result.data["results"] == [
        {
            "title": "Python",
            "url": "https://www.python.org/",
            "snippet": "Python is a high-level programming language.",
            "source": "duckduckgo",
        },
        {
            "title": "Python Package Index",
            "url": "https://pypi.org/",
            "snippet": "Python Package Index - The official third-party software repository for Python.",
            "source": "duckduckgo",
        },
    ]


def test_web_search_returns_empty_results_when_html_has_no_matches() -> None:
    result = WebSearchTool(html_fetcher=lambda url, timeout: "<html></html>").run({"query": "missing"})

    assert result.success is True
    assert result.error is None
    assert result.data["results"] == []
    assert result.data["message"] == "No real web search results found."


def test_web_search_returns_error_for_empty_query() -> None:
    result = WebSearchTool().run({"query": "   "})

    assert result.success is False
    assert result.data == {}
    assert result.error == "Query must be a non-empty string."


def test_web_search_returns_error_when_request_fails() -> None:
    def broken_fetcher(url: str, timeout: float) -> str:
        raise OSError("network unavailable")

    result = WebSearchTool(html_fetcher=broken_fetcher).run({"query": "Python"})

    assert result.success is False
    assert result.data == {}
    assert result.error == "Real web search failed: network unavailable"


def test_todo_creates_todo_in_session() -> None:
    session = SessionState(user_id="user-1", session_id="session-1")
    result = TodoTool().run(
        {
            "session": session,
            "operation": "create",
            "title": "Write tests",
        }
    )

    assert result.success is True
    assert result.data["todo"] == {"id": 1, "title": "Write tests", "completed": False}
    assert session.todos == [{"id": 1, "title": "Write tests", "completed": False}]


def test_todo_lists_todos_in_session() -> None:
    session = SessionState(
        user_id="user-1",
        session_id="session-1",
        todos=[{"id": 1, "title": "Write tests", "completed": False}],
    )

    result = TodoTool().run({"session": session, "operation": "list"})

    assert result.success is True
    assert result.data["todos"] == [{"id": 1, "title": "Write tests", "completed": False}]


def test_todo_completes_todo_in_session() -> None:
    session = SessionState(
        user_id="user-1",
        session_id="session-1",
        todos=[{"id": 1, "title": "Write tests", "completed": False}],
    )

    result = TodoTool().run({"session": session, "operation": "complete", "id": 1})

    assert result.success is True
    assert result.data["todo"]["completed"] is True
    assert session.todos[0]["completed"] is True


def test_todo_deletes_todo_in_session() -> None:
    session = SessionState(
        user_id="user-1",
        session_id="session-1",
        todos=[{"id": 1, "title": "Write tests", "completed": False}],
    )

    result = TodoTool().run({"session": session, "operation": "delete", "id": 1})

    assert result.success is True
    assert result.data["todo"] == {"id": 1, "title": "Write tests", "completed": False}
    assert session.todos == []


def test_todo_sessions_are_isolated() -> None:
    first_session = SessionState(user_id="user-1", session_id="session-1")
    second_session = SessionState(user_id="user-1", session_id="session-2")
    tool = TodoTool()

    tool.run({"session": first_session, "operation": "create", "title": "First session todo"})
    tool.run({"session": second_session, "operation": "create", "title": "Second session todo"})

    assert first_session.todos == [{"id": 1, "title": "First session todo", "completed": False}]
    assert second_session.todos == [{"id": 1, "title": "Second session todo", "completed": False}]
