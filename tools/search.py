from __future__ import annotations

import json
from html.parser import HTMLParser
from typing import Any
from urllib.error import URLError
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

from tools.registry import BaseTool, ToolResult


class MockSearchTool(BaseTool):
    name = "mock_search"
    description = "Search a small built-in mock dataset without using the network."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search keywords for the mock dataset.",
            }
        },
        "required": ["query"],
    }

    _mock_data = [
        {
            "title": "Python 是什么",
            "keywords": ["python", "Python", "编程", "语言"],
            "snippet": "Python 是一种易读、通用的编程语言，常用于脚本、Web、数据分析和自动化。",
        },
        {
            "title": "北京天气",
            "keywords": ["北京", "天气", "beijing", "weather"],
            "snippet": "Mock 天气结果：北京今天多云，气温 24-31 摄氏度。",
        },
        {
            "title": "苹果手机价格",
            "keywords": ["苹果", "手机", "iphone", "价格"],
            "snippet": "Mock 价格结果：苹果手机价格会随型号和渠道变化，这里仅为演示数据。",
        },
        {
            "title": "Agent 工具注册中心",
            "keywords": ["agent", "工具", "注册", "registry"],
            "snippet": "工具注册中心用于登记工具、查询工具和导出工具 schema。",
        },
    ]

    def run(self, arguments: dict[str, Any]) -> ToolResult:
        query = arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            return ToolResult(success=False, error="Query must be a non-empty string.")

        normalized_query = query.strip().lower()
        results = [
            {
                "title": item["title"],
                "snippet": item["snippet"],
                "source": "mock",
            }
            for item in self._mock_data
            if self._matches(normalized_query, item)
        ]

        if not results:
            return ToolResult(
                success=True,
                data={
                    "results": [],
                    "message": "No mock search results found. This is not a real internet search.",
                },
            )

        return ToolResult(
            success=True,
            data={
                "results": results,
                "message": "Mock search results only. This is not a real internet search.",
            },
        )

    def _matches(self, normalized_query: str, item: dict[str, Any]) -> bool:
        searchable_parts = [item["title"], item["snippet"], *item["keywords"]]
        return any(part.lower() in normalized_query or normalized_query in part.lower() for part in searchable_parts)


class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Search the live web through DuckDuckGo and return real internet results."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search keywords for the live internet.",
            }
        },
        "required": ["query"],
    }

    search_url = "https://duckduckgo.com/html/?q={query}"
    instant_answer_url = "https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"
    user_agent = "Mozilla/5.0 (compatible; LocalAgent/1.0; +https://duckduckgo.com/html/)"

    def __init__(self, timeout: float = 10.0, max_results: int = 5, html_fetcher: Any | None = None) -> None:
        self.timeout = timeout
        self.max_results = max_results
        self._html_fetcher = html_fetcher

    def run(self, arguments: dict[str, Any]) -> ToolResult:
        query = arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            return ToolResult(success=False, error="Query must be a non-empty string.")

        normalized_query = query.strip()
        url = self.search_url.format(query=quote_plus(normalized_query))

        try:
            html = self._fetch_text(url)
            results = _parse_duckduckgo_results(html, self.max_results)
        except (OSError, TimeoutError, URLError, ValueError) as exc:
            return ToolResult(success=False, error=f"Real web search failed: {exc}")

        if not results:
            try:
                api_url = self.instant_answer_url.format(query=quote_plus(normalized_query))
                payload = self._fetch_text(api_url)
                results = _parse_duckduckgo_instant_answer_results(payload, self.max_results)
            except (OSError, TimeoutError, URLError, ValueError, json.JSONDecodeError):
                results = []

        if not results:
            return ToolResult(
                success=True,
                data={
                    "query": normalized_query,
                    "results": [],
                    "message": "No real web search results found.",
                },
            )

        return ToolResult(
            success=True,
            data={
                "query": normalized_query,
                "results": results,
                "message": "Real web search results from DuckDuckGo.",
            },
        )

    def _fetch_text(self, url: str) -> str:
        if self._html_fetcher is not None:
            return self._html_fetcher(url, self.timeout)

        request = Request(url, headers={"User-Agent": self.user_agent})
        with urlopen(request, timeout=self.timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")


class _DuckDuckGoHTMLParser(HTMLParser):
    def __init__(self, max_results: int) -> None:
        super().__init__(convert_charrefs=True)
        self.max_results = max_results
        self.results: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None
        self._capture_field: str | None = None
        self._capture_tag: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {name: value or "" for name, value in attrs}
        classes = set(attr_map.get("class", "").split())

        if tag == "a" and "result__a" in classes:
            self._finish_current()
            self._current = {
                "title": "",
                "url": _normalize_duckduckgo_url(attr_map.get("href", "")),
                "snippet": "",
                "source": "duckduckgo",
            }
            self._capture_field = "title"
            self._capture_tag = tag
            return

        if self._current is not None and "result__snippet" in classes:
            self._capture_field = "snippet"
            self._capture_tag = tag

    def handle_data(self, data: str) -> None:
        if self._current is None or self._capture_field is None:
            return

        existing = self._current[self._capture_field]
        separator = " " if existing and not existing.endswith(" ") else ""
        self._current[self._capture_field] = f"{existing}{separator}{data.strip()}".strip()

    def handle_endtag(self, tag: str) -> None:
        if self._capture_tag == tag:
            self._capture_field = None
            self._capture_tag = None

    def close(self) -> None:
        super().close()
        self._finish_current()

    def _finish_current(self) -> None:
        if len(self.results) >= self.max_results:
            self._current = None
            return

        if self._current is None:
            return

        if self._current["title"]:
            self.results.append(self._current)

        self._current = None


def _parse_duckduckgo_results(html: str, max_results: int) -> list[dict[str, str]]:
    parser = _DuckDuckGoHTMLParser(max_results=max_results)
    parser.feed(html)
    parser.close()
    return parser.results[:max_results]


def _parse_duckduckgo_instant_answer_results(payload: str, max_results: int) -> list[dict[str, str]]:
    data = json.loads(payload)
    if not isinstance(data, dict):
        return []

    results: list[dict[str, str]] = []
    heading = str(data.get("Heading") or "").strip()
    abstract = str(data.get("AbstractText") or "").strip()
    abstract_url = str(data.get("AbstractURL") or "").strip()
    if heading and (abstract or abstract_url):
        results.append(
            {
                "title": heading,
                "url": abstract_url,
                "snippet": abstract,
                "source": "duckduckgo",
            }
        )

    for topic in _iter_related_topics(data.get("RelatedTopics", [])):
        if len(results) >= max_results:
            break

        text = str(topic.get("Text") or "").strip()
        url = str(topic.get("FirstURL") or "").strip()
        if not text:
            continue

        title = text.split(" - ", 1)[0].strip() or text
        results.append(
            {
                "title": title,
                "url": url,
                "snippet": text,
                "source": "duckduckgo",
            }
        )

    return results[:max_results]


def _iter_related_topics(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    topics: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        if isinstance(item.get("Topics"), list):
            topics.extend(_iter_related_topics(item["Topics"]))
        else:
            topics.append(item)

    return topics


def _normalize_duckduckgo_url(url: str) -> str:
    if not url:
        return ""

    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    redirect_target = query.get("uddg")
    if redirect_target:
        return unquote(redirect_target[0])

    return url
