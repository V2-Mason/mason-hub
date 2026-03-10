"""Scout v2 搜索工具统一接口

支持 3 个搜索源：
- GitHub API（无需认证，60次/h rate limit）
- SearXNG（Google + Twitter + 更多引擎）
- DuckDuckGo（免费 fallback）
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import quote_plus, urlencode
import json
import logging
import re
import requests

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "MasonHub-Scout/2.0 (https://github.com/V2-Mason)"
}
# DuckDuckGo HTML API 需要浏览器 UA，否则返回 202 空页面
_BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
TIMEOUT = 10  # seconds


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str        # "github" / "google" / "twitter" / "duckduckgo"
    date: str = ""     # 发布日期（如果有）
    stars: int = 0     # GitHub 专用
    language: str = "" # GitHub 专用
    extra: dict = field(default_factory=dict)


class GitHubSearch:
    """GitHub REST API 搜索 — 无需认证（rate limit 60次/h）"""

    BASE_URL = "https://api.github.com"

    def search_repos(self, query: str, since_days: int = 7, limit: int = 10) -> list[SearchResult]:
        """搜索 GitHub 仓库，按 stars 排序，支持 created:>YYYY-MM-DD 过滤"""
        since_date = (datetime.utcnow() - timedelta(days=since_days)).strftime("%Y-%m-%d")
        q = f"{query} created:>{since_date}"
        params = {
            "q": q,
            "sort": "stars",
            "order": "desc",
            "per_page": min(limit, 100),
        }
        try:
            resp = requests.get(
                f"{self.BASE_URL}/search/repositories",
                params=params,
                headers={**HEADERS, "Accept": "application/vnd.github.v3+json"},
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.warning(f"GitHub search failed: {e}")
            return []

        results = []
        for item in data.get("items", [])[:limit]:
            results.append(SearchResult(
                title=item.get("full_name", ""),
                url=item.get("html_url", ""),
                snippet=item.get("description", "") or "",
                source="github",
                date=item.get("created_at", "")[:10],
                stars=item.get("stargazers_count", 0),
                language=item.get("language", "") or "",
                extra={
                    "forks": item.get("forks_count", 0),
                    "open_issues": item.get("open_issues_count", 0),
                    "topics": item.get("topics", []),
                },
            ))
        return results

    def search_topics(self, query: str, limit: int = 10) -> list[SearchResult]:
        """搜索 GitHub topics"""
        params = {
            "q": query,
            "per_page": min(limit, 100),
        }
        try:
            resp = requests.get(
                f"{self.BASE_URL}/search/topics",
                params=params,
                headers={
                    **HEADERS,
                    "Accept": "application/vnd.github.mercy-preview+json",
                },
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.warning(f"GitHub topics search failed: {e}")
            return []

        results = []
        for item in data.get("items", [])[:limit]:
            name = item.get("name", "")
            results.append(SearchResult(
                title=item.get("display_name") or name,
                url=f"https://github.com/topics/{name}",
                snippet=item.get("short_description") or item.get("description") or "",
                source="github",
                date=item.get("created_at", "")[:10] if item.get("created_at") else "",
                extra={
                    "curated": item.get("curated", False),
                    "featured": item.get("featured", False),
                },
            ))
        return results


class SearXNGSearch:
    """SearXNG 统一搜索 — 内置 Google + Twitter + 更多引擎"""

    def __init__(self, base_url: str = "http://localhost:8888"):
        self.base_url = base_url.rstrip("/")
        self.available = self._check_available()

    def _check_available(self) -> bool:
        """检查 SearXNG 是否运行（验证响应确实是 SearXNG，不是其他服务）"""
        try:
            # SearXNG /healthz 返回纯文本 "OK"，不是 HTML/JSON
            r = requests.get(f"{self.base_url}/healthz", timeout=3)
            if r.status_code != 200:
                return False
            # 额外验证：SearXNG healthz 返回很短的文本，不是 HTML 页面
            body = r.text.strip()
            if len(body) > 100 or "<html" in body.lower():
                return False
            return True
        except Exception:
            return False

    def search(self, query: str, engines: list[str] = None, limit: int = 10) -> list[SearchResult]:
        """通用搜索 — GET /search with format=json"""
        if not self.available:
            logger.warning("SearXNG not available, returning empty results")
            return []

        params = {
            "q": query,
            "format": "json",
            "pageno": 1,
        }
        if engines:
            params["engines"] = ",".join(engines)

        try:
            resp = requests.get(
                f"{self.base_url}/search",
                params=params,
                headers=HEADERS,
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.warning(f"SearXNG search failed: {e}")
            return []

        results = []
        for item in data.get("results", [])[:limit]:
            # 推断 source：看 engine 列表
            item_engines = item.get("engines", [])
            if "twitter" in item_engines:
                source = "twitter"
            elif "google" in item_engines:
                source = "google"
            else:
                source = item_engines[0] if item_engines else "searxng"

            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("content", "") or "",
                source=source,
                date=item.get("publishedDate", "")[:10] if item.get("publishedDate") else "",
                extra={
                    "engines": item_engines,
                    "score": item.get("score", 0),
                },
            ))
        return results

    def search_google(self, query: str, limit: int = 10) -> list[SearchResult]:
        return self.search(query, engines=["google"], limit=limit)

    def search_twitter(self, query: str, limit: int = 10) -> list[SearchResult]:
        return self.search(query, engines=["twitter"], limit=limit)


class DuckDuckGoSearch:
    """DuckDuckGo 搜索 — 免费 fallback，无需 API key

    策略：先试 instant answer JSON API，结果不够则用 HTML API + regex 解析。
    """

    INSTANT_URL = "https://api.duckduckgo.com/"
    HTML_URL = "https://html.duckduckgo.com/html/"

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """搜索 DuckDuckGo，先试 instant answer，不够则 HTML fallback"""
        results = self._search_instant(query, limit)
        if len(results) < limit:
            html_results = self._search_html(query, limit - len(results))
            # 去重（按 URL）
            seen_urls = {r.url for r in results}
            for r in html_results:
                if r.url not in seen_urls:
                    results.append(r)
                    seen_urls.add(r.url)
        return results[:limit]

    def _search_instant(self, query: str, limit: int) -> list[SearchResult]:
        """DuckDuckGo Instant Answer API — 结构化但结果有限"""
        params = {
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1",
        }
        try:
            resp = requests.get(
                self.INSTANT_URL,
                params=params,
                headers={"User-Agent": _BROWSER_UA},
                timeout=TIMEOUT,
            )
            if resp.status_code == 202:
                logger.warning("DuckDuckGo instant API returned 202 (bot detection)")
                return []
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError) as e:
            logger.warning(f"DuckDuckGo instant API failed: {e}")
            return []

        results = []

        # Abstract（主要结果）
        if data.get("AbstractURL") and data.get("AbstractText"):
            results.append(SearchResult(
                title=data.get("Heading", query),
                url=data["AbstractURL"],
                snippet=data["AbstractText"][:300],
                source="duckduckgo",
                extra={"type": "abstract"},
            ))

        # RelatedTopics
        for topic in data.get("RelatedTopics", []):
            if len(results) >= limit:
                break
            if "FirstURL" in topic and "Text" in topic:
                results.append(SearchResult(
                    title=topic.get("Text", "")[:120],
                    url=topic["FirstURL"],
                    snippet=topic.get("Text", "")[:300],
                    source="duckduckgo",
                    extra={"type": "related"},
                ))
            # 处理嵌套的子 topics
            for sub in topic.get("Topics", []):
                if len(results) >= limit:
                    break
                if "FirstURL" in sub and "Text" in sub:
                    results.append(SearchResult(
                        title=sub.get("Text", "")[:120],
                        url=sub["FirstURL"],
                        snippet=sub.get("Text", "")[:300],
                        source="duckduckgo",
                        extra={"type": "related"},
                    ))

        # Results 字段
        for item in data.get("Results", []):
            if len(results) >= limit:
                break
            if "FirstURL" in item:
                results.append(SearchResult(
                    title=item.get("Text", "")[:120],
                    url=item["FirstURL"],
                    snippet=item.get("Text", "")[:300],
                    source="duckduckgo",
                    extra={"type": "result"},
                ))

        return results

    def _search_html(self, query: str, limit: int) -> list[SearchResult]:
        """DuckDuckGo HTML API — 用 regex 解析，不依赖 beautifulsoup"""
        try:
            resp = requests.post(
                self.HTML_URL,
                data={"q": query, "b": ""},
                headers={
                    "User-Agent": _BROWSER_UA,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=TIMEOUT,
            )
            if resp.status_code == 202:
                logger.warning("DuckDuckGo HTML API returned 202 (bot detection)")
                return []
            resp.raise_for_status()
            html = resp.text
        except requests.RequestException as e:
            logger.warning(f"DuckDuckGo HTML search failed: {e}")
            return []

        results = []

        from html import unescape
        from urllib.parse import unquote

        # 按 web-result 块拆分，跳过广告（result--ad）
        blocks = re.split(r'(?=<div[^>]*class="[^"]*web-result[^"]*")', html)

        for block in blocks:
            if len(results) >= limit:
                break

            # 跳过广告块
            if "result--ad" in block[:200]:
                continue

            # 提取链接
            link_match = re.search(
                r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
                block,
                re.DOTALL,
            )
            if not link_match:
                continue

            href = link_match.group(1)
            title_html = link_match.group(2)

            # 提取摘要
            snip_match = re.search(
                r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
                block,
                re.DOTALL,
            )

            # 清理 HTML 标签和实体
            title = unescape(re.sub(r"<[^>]+>", "", title_html)).strip()
            snippet = ""
            if snip_match:
                snippet = unescape(re.sub(r"<[^>]+>", "", snip_match.group(1))).strip()

            # DDG 的 href 可能是 redirect URL，提取真实 URL
            url_match = re.search(r"uddg=([^&]+)", href)
            if url_match:
                url = unquote(url_match.group(1))
            else:
                url = unescape(href)

            if title and url:
                results.append(SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    source="duckduckgo",
                    extra={"type": "html"},
                ))

        return results


# 技术类关键词（用于 auto 模式判断）
_TECH_KEYWORDS = {
    "github", "repo", "library", "framework", "sdk", "api", "cli",
    "open source", "开源", "工具", "tool", "agent", "mcp", "llm",
    "comfyui", "docker", "kubernetes", "rust", "python", "typescript",
}


class UnifiedSearch:
    """统一搜索接口 — 按配置和可用性自动选择搜索源"""

    def __init__(self, config: dict = None):
        config = config or {}
        self.github = GitHubSearch()
        self.searxng = SearXNGSearch(
            config.get("searxng_url", "http://localhost:8888")
        )
        self.ddg = DuckDuckGoSearch()

    def search(self, query: str, source: str = "auto", limit: int = 10) -> list[SearchResult]:
        """统一搜索

        source: "github" / "google" / "twitter" / "web" / "auto"

        auto 逻辑：
        - 技术类关键词 -> github 优先
        - 其他 -> SearXNG 优先，不可用则 DuckDuckGo
        """
        if source == "github":
            return self.github.search_repos(query, limit=limit)

        if source == "google":
            if self.searxng.available:
                return self.searxng.search_google(query, limit=limit)
            logger.info("SearXNG unavailable, falling back to DuckDuckGo for google search")
            return self.ddg.search(query, limit=limit)

        if source == "twitter":
            if self.searxng.available:
                return self.searxng.search_twitter(query, limit=limit)
            logger.warning("SearXNG unavailable, no Twitter fallback")
            return []

        if source == "web":
            if self.searxng.available:
                return self.searxng.search(query, limit=limit)
            return self.ddg.search(query, limit=limit)

        # auto 模式
        query_lower = query.lower()
        is_tech = any(kw in query_lower for kw in _TECH_KEYWORDS)

        if is_tech:
            results = self.github.search_repos(query, limit=limit)
            if results:
                return results
            # GitHub 没结果，fallback 到 web
            logger.info(f"GitHub returned no results for '{query}', falling back to web")

        if self.searxng.available:
            return self.searxng.search(query, limit=limit)
        return self.ddg.search(query, limit=limit)

    def search_multi(self, query: str, sources: list[str] = None, limit_per_source: int = 5) -> list[SearchResult]:
        """多源搜索 — 同时搜多个源，合并去重"""
        if sources is None:
            sources = ["github", "web"]

        all_results = []
        seen_urls = set()

        for src in sources:
            results = self.search(query, source=src, limit=limit_per_source)
            for r in results:
                if r.url not in seen_urls:
                    all_results.append(r)
                    seen_urls.add(r.url)

        return all_results

    def get_available_sources(self) -> list[str]:
        """返回当前可用的搜索源列表"""
        sources = ["github", "duckduckgo"]  # 这两个始终可用
        if self.searxng.available:
            sources.extend(["google", "twitter", "searxng"])
        return sources


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    search = UnifiedSearch()
    print(f"可用搜索源: {search.get_available_sources()}")

    # 测试 GitHub
    results = search.search("claude code agent", source="github", limit=3)
    print(f"\nGitHub 搜索: {len(results)} 条结果")
    for r in results:
        print(f"  {r.title} -- {r.url}")

    # 测试 Web (DuckDuckGo fallback)
    results = search.search("韩国护肤品 跨境电商", source="web", limit=3)
    print(f"\nWeb 搜索: {len(results)} 条结果")
    for r in results:
        print(f"  {r.title} -- {r.url}")
