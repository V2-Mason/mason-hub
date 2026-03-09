#!/usr/bin/env python3
"""Semantic Snapshot — extract clean, structured content from web pages.

Reduces token usage when agents need to process web content by stripping
chrome, ads, nav, and converting to clean Markdown.

Usage:
    # Basic extraction (auto-detect page type)
    python skills/semantic_snapshot.py https://example.com

    # Static page (no JavaScript, uses requests+bs4)
    python skills/semantic_snapshot.py https://news.ycombinator.com --no-js

    # JSON output with metadata
    python skills/semantic_snapshot.py https://example.com --json --max-chars 5000

    # Interactive page with ARIA snapshot
    python skills/semantic_snapshot.py https://app.example.com --mode interactive

    # Wait for dynamic content
    python skills/semantic_snapshot.py https://spa.example.com --wait-selector ".main-content"

    # Output to file
    python skills/semantic_snapshot.py https://example.com --output snapshot.md
"""

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlparse

# ---------------------------------------------------------------------------
# Conditional imports — fail gracefully with clear messages
# ---------------------------------------------------------------------------

try:
    from bs4 import BeautifulSoup, NavigableString, Tag
    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False

try:
    from playwright.async_api import async_playwright, TimeoutError as PwTimeout
    _HAS_PLAYWRIGHT = True
except ImportError:
    _HAS_PLAYWRIGHT = False

try:
    import requests as _requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

CST = timezone(timedelta(hours=8))

CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

STEALTH_ARGS = [
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-blink-features=AutomationControlled",
    "--disable-features=IsolateOrigins,site-per-process",
    "--no-first-run",
    "--no-default-browser-check",
]

# Selectors tried in order for main content detection
CONTENT_SELECTORS = [
    "article",
    "main",
    "[role='main']",
    ".content",
    ".post-body",
    "#content",
    ".article-content",
    ".entry-content",
    ".post-content",
]

# Tags to strip entirely (including their content)
STRIP_TAGS = {"script", "style", "noscript", "svg", "iframe", "object", "embed"}

# Navigation-related tags/classes
NAV_SELECTORS = ["nav", "header", "footer", "[role='navigation']", "[role='banner']",
                 "[role='contentinfo']", ".navbar", ".nav", ".sidebar", ".menu",
                 ".breadcrumb", ".pagination"]

FORM_SELECTORS = ["form", ".form-group", ".login-form", ".search-form"]


# ===================================================================
# Section 1: Page Loader
# ===================================================================

async def load_page_playwright(url: str, timeout: int = 15000,
                               wait_selector: str | None = None) -> tuple[str, str]:
    """Load page with Playwright, return (html, title)."""
    if not _HAS_PLAYWRIGHT:
        print("ERROR: playwright not installed. Use --no-js or install playwright.", file=sys.stderr)
        sys.exit(1)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=STEALTH_ARGS,
        )
        context = await browser.new_context(user_agent=CHROME_UA)
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            # Try to upgrade to networkidle with a shorter timeout
            try:
                await page.wait_for_load_state("networkidle", timeout=min(timeout, 5000))
            except Exception:
                pass  # domcontentloaded is sufficient

            if wait_selector:
                await page.wait_for_selector(wait_selector, timeout=timeout)

            title = await page.title()
            html = await page.content()
        except PwTimeout:
            print(f"WARNING: Timeout loading {url}, using partial content", file=sys.stderr)
            title = await page.title() or ""
            html = await page.content()
        finally:
            await browser.close()

    return html, title


def load_page_static(url: str, timeout: int = 15) -> tuple[str, str]:
    """Load page with requests (no JS), return (html, title)."""
    if not _HAS_REQUESTS:
        print("ERROR: requests not installed.", file=sys.stderr)
        sys.exit(1)

    headers = {"User-Agent": CHROME_UA}
    try:
        resp = _requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        html = resp.text
    except _requests.RequestException as e:
        print(f"ERROR: Failed to fetch {url}: {e}", file=sys.stderr)
        sys.exit(1)

    soup = _get_soup(html)
    title = soup.title.get_text(strip=True) if soup.title else ""
    return html, title


def load_local_file(path: str) -> tuple[str, str]:
    """Load a local HTML file, return (html, title)."""
    p = Path(path)
    if not p.exists():
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        sys.exit(1)
    html = p.read_text(encoding="utf-8", errors="replace")
    soup = _get_soup(html)
    title = soup.title.get_text(strip=True) if soup.title else p.stem
    return html, title


# ===================================================================
# Section 2: Page Type Detector
# ===================================================================

def detect_page_type(soup: BeautifulSoup) -> str:
    """Detect page type from DOM structure. Returns 'article', 'table', or 'interactive'."""

    # Check for article indicators
    for sel in ("article", "main", "[role='main']"):
        elements = soup.select(sel)
        for el in elements:
            text = el.get_text(strip=True)
            if len(text) > 500:
                return "article"

    # Check for table-heavy pages
    tables = soup.find_all("table")
    big_tables = [t for t in tables if len(t.find_all("tr")) > 3]
    if len(big_tables) >= 1:
        return "table"

    # Check for interactive/form-heavy pages
    forms = soup.find_all("form")
    inputs = soup.find_all("input")
    buttons = soup.find_all("button")
    if len(forms) >= 2 or (len(inputs) + len(buttons)) > 10:
        return "interactive"

    # Default
    return "article"


# ===================================================================
# Section 3: Content Extractors
# ===================================================================

def _get_soup(html: str) -> BeautifulSoup:
    """Create a BeautifulSoup instance, preferring lxml parser."""
    try:
        import lxml  # noqa: F401
        return BeautifulSoup(html, "lxml")
    except ImportError:
        return BeautifulSoup(html, "html.parser")


def _strip_unwanted(soup: BeautifulSoup, include_nav: bool = False,
                    include_forms: bool = False) -> None:
    """Remove unwanted elements from soup in-place."""
    # Always strip script/style/etc.
    for tag_name in STRIP_TAGS:
        for el in soup.find_all(tag_name):
            el.decompose()

    # Strip nav unless requested
    if not include_nav:
        for sel in NAV_SELECTORS:
            for el in soup.select(sel):
                el.decompose()

    # Strip forms unless requested
    if not include_forms:
        for sel in FORM_SELECTORS:
            for el in soup.select(sel):
                el.decompose()


def _find_main_content(soup: BeautifulSoup) -> Tag | None:
    """Find the main content element via selector cascade, then largest-text fallback."""
    for sel in CONTENT_SELECTORS:
        elements = soup.select(sel)
        for el in elements:
            text = el.get_text(strip=True)
            if len(text) > 200:
                return el

    # Fallback: find the element with the most text
    best = None
    best_len = 0
    for el in soup.find_all(["div", "section", "td"]):
        text_len = len(el.get_text(strip=True))
        if text_len > best_len:
            best_len = text_len
            best = el

    return best


def _element_to_markdown(el: Tag | NavigableString, base_url: str = "") -> str:
    """Recursively convert an HTML element to Markdown."""
    if isinstance(el, NavigableString):
        text = str(el)
        # Collapse whitespace but preserve single newlines within text
        text = re.sub(r'[ \t]+', ' ', text)
        return text

    if not isinstance(el, Tag):
        return ""

    tag = el.name.lower() if el.name else ""

    # Skip decomposed / hidden elements
    if tag in STRIP_TAGS:
        return ""

    # Headings
    if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
        level = int(tag[1])
        prefix = "#" * level
        inner = _children_to_md(el, base_url).strip()
        if inner:
            return f"\n\n{prefix} {inner}\n\n"
        return ""

    # Paragraphs
    if tag == "p":
        inner = _children_to_md(el, base_url).strip()
        if inner:
            return f"\n\n{inner}\n\n"
        return ""

    # Line breaks
    if tag == "br":
        return "\n"

    # Horizontal rule
    if tag == "hr":
        return "\n\n---\n\n"

    # Links
    if tag == "a":
        href = el.get("href", "")
        inner = _children_to_md(el, base_url).strip()
        if not inner:
            return ""
        if href and not href.startswith(("javascript:", "#", "mailto:")):
            if base_url and not href.startswith(("http://", "https://")):
                href = urljoin(base_url, href)
            return f"[{inner}]({href})"
        return inner

    # Images
    if tag == "img":
        alt = el.get("alt", "").strip()
        src = el.get("src", "")
        if alt and src:
            if base_url and not src.startswith(("http://", "https://", "data:")):
                src = urljoin(base_url, src)
            return f"![{alt}]({src})"
        return ""

    # Bold / strong
    if tag in ("strong", "b"):
        inner = _children_to_md(el, base_url).strip()
        if inner:
            return f"**{inner}**"
        return ""

    # Italic / emphasis
    if tag in ("em", "i"):
        inner = _children_to_md(el, base_url).strip()
        if inner:
            return f"*{inner}*"
        return ""

    # Inline code
    if tag == "code" and (not el.parent or el.parent.name != "pre"):
        inner = el.get_text()
        if inner:
            return f"`{inner}`"
        return ""

    # Code blocks
    if tag == "pre":
        code_el = el.find("code")
        if code_el:
            code_text = code_el.get_text()
        else:
            code_text = el.get_text()
        lang = ""
        if code_el:
            cls = code_el.get("class", [])
            for c in cls:
                if c.startswith("language-"):
                    lang = c[9:]
                    break
        return f"\n\n```{lang}\n{code_text}\n```\n\n"

    # Lists
    if tag in ("ul", "ol"):
        items = []
        for i, li in enumerate(el.find_all("li", recursive=False)):
            inner = _children_to_md(li, base_url).strip()
            if inner:
                if tag == "ol":
                    items.append(f"{i + 1}. {inner}")
                else:
                    items.append(f"- {inner}")
        if items:
            return "\n\n" + "\n".join(items) + "\n\n"
        return ""

    # Skip li if handled by parent ul/ol
    if tag == "li":
        inner = _children_to_md(el, base_url).strip()
        return inner

    # Tables
    if tag == "table":
        return _table_to_markdown(el, base_url)

    # Blockquote
    if tag == "blockquote":
        inner = _children_to_md(el, base_url).strip()
        if inner:
            quoted = "\n".join(f"> {line}" for line in inner.split("\n"))
            return f"\n\n{quoted}\n\n"
        return ""

    # Default: recurse into children
    return _children_to_md(el, base_url)


def _children_to_md(el: Tag, base_url: str = "") -> str:
    """Convert all children of an element to Markdown."""
    parts = []
    for child in el.children:
        parts.append(_element_to_markdown(child, base_url))
    return "".join(parts)


def _table_to_markdown(table: Tag, base_url: str = "") -> str:
    """Convert an HTML table to Markdown table format."""
    rows = table.find_all("tr")
    if not rows:
        return ""

    md_rows = []
    for row in rows:
        cells = row.find_all(["th", "td"])
        cell_texts = []
        for c in cells:
            text = _children_to_md(c, base_url).strip()
            # Clean up for table cell (no newlines)
            text = re.sub(r'\s+', ' ', text)
            cell_texts.append(text)
        md_rows.append("| " + " | ".join(cell_texts) + " |")

    if not md_rows:
        return ""

    # Add separator after first row (header)
    first_row_cells = rows[0].find_all(["th", "td"])
    separator = "| " + " | ".join(["---"] * len(first_row_cells)) + " |"
    result = md_rows[0] + "\n" + separator
    if len(md_rows) > 1:
        result += "\n" + "\n".join(md_rows[1:])

    return f"\n\n{result}\n\n"


def extract_article(html: str, base_url: str = "",
                    include_nav: bool = False,
                    include_forms: bool = False) -> str:
    """Extract article content as Markdown."""
    if not _HAS_BS4:
        print("ERROR: beautifulsoup4 not installed.", file=sys.stderr)
        sys.exit(1)

    soup = _get_soup(html)
    _strip_unwanted(soup, include_nav=include_nav, include_forms=include_forms)

    main_el = _find_main_content(soup)
    if main_el is None:
        main_el = soup.body or soup

    md = _element_to_markdown(main_el, base_url)

    # Clean up excessive whitespace
    md = re.sub(r'\n{3,}', '\n\n', md)
    md = md.strip()
    return md


def extract_tables(html: str, base_url: str = "") -> str:
    """Extract all significant tables as Markdown."""
    if not _HAS_BS4:
        print("ERROR: beautifulsoup4 not installed.", file=sys.stderr)
        sys.exit(1)

    soup = _get_soup(html)
    _strip_unwanted(soup)

    tables = soup.find_all("table")
    parts = []
    for i, table in enumerate(tables):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        # Try to find a caption or preceding heading
        caption = table.find("caption")
        heading = ""
        if caption:
            heading = f"### {caption.get_text(strip=True)}\n\n"
        md = _table_to_markdown(table, base_url)
        if md.strip():
            parts.append(f"{heading}{md.strip()}")

    return "\n\n".join(parts) if parts else extract_article(html, base_url)


async def extract_interactive(html: str, url: str,
                              timeout: int = 15000,
                              wait_selector: str | None = None,
                              include_nav: bool = False,
                              include_forms: bool = False) -> str:
    """Extract interactive page using Playwright ARIA snapshot, with fallback."""
    if not _HAS_PLAYWRIGHT:
        return extract_article(html, url, include_nav=include_nav, include_forms=include_forms)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=STEALTH_ARGS)
            context = await browser.new_context(user_agent=CHROME_UA)
            page = await context.new_page()

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                try:
                    await page.wait_for_load_state("networkidle", timeout=min(timeout, 5000))
                except Exception:
                    pass
                if wait_selector:
                    await page.wait_for_selector(wait_selector, timeout=timeout)

                aria_text = await page.locator("body").aria_snapshot()
            finally:
                await browser.close()

        # Post-process ARIA snapshot
        return _postprocess_aria(aria_text)

    except Exception as e:
        print(f"WARNING: ARIA snapshot failed ({e}), falling back to article extractor",
              file=sys.stderr)
        return extract_article(html, url, include_nav=include_nav, include_forms=include_forms)


def _postprocess_aria(text: str) -> str:
    """Clean up ARIA snapshot output."""
    lines = text.split("\n")
    result = []
    link_buffer = []

    def flush_links():
        nonlocal link_buffer
        if len(link_buffer) > 10:
            shown = link_buffer[:10]
            remaining = len(link_buffer) - 10
            result.append(f"[Nav: {' | '.join(shown)} ... and {remaining} more]")
        elif len(link_buffer) > 3:
            result.append(f"[Nav: {' | '.join(link_buffer)}]")
        elif link_buffer:
            for lb in link_buffer:
                result.append(f"- {lb}")
        link_buffer = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Detect link sequences
        link_match = re.match(r'^-?\s*link\s+"(.+?)"', stripped)
        if link_match:
            link_buffer.append(link_match.group(1))
            continue

        # Flush accumulated links before non-link content
        if link_buffer:
            flush_links()

        # Strip image nodes without alt text
        if re.match(r'^-?\s*img\s*$', stripped):
            continue

        # Collapse single-child nesting: "  - group: \n    - text: X" → "X"
        result.append(stripped)

    if link_buffer:
        flush_links()

    return "\n".join(result)


# ===================================================================
# Section 4: Output Formatter
# ===================================================================

def format_output(content: str, title: str, url: str, mode: str,
                  html_chars: int, max_chars: int,
                  as_json: bool = False) -> str:
    """Format extracted content with metadata header."""
    now = datetime.now(CST).strftime("%Y-%m-%d %H:%M CST")
    char_count = len(content)

    # Smart truncation at paragraph boundary
    if max_chars and len(content) > max_chars:
        truncated = content[:max_chars]
        # Try to cut at last paragraph break
        last_para = truncated.rfind("\n\n")
        if last_para > max_chars * 0.7:
            truncated = truncated[:last_para]
        content = truncated + f"\n\n[... truncated at {max_chars} chars]"
        char_count = len(content)

    compression = f"{html_chars / max(char_count, 1):.1f}x" if char_count > 0 else "N/A"

    if as_json:
        return json.dumps({
            "url": url,
            "title": title,
            "mode": mode,
            "char_count": char_count,
            "html_char_count": html_chars,
            "compression_ratio": round(html_chars / max(char_count, 1), 2),
            "content": content,
            "extracted_at": now,
        }, ensure_ascii=False, indent=2)

    header = (
        f"# {title}\n"
        f"> Source: {url}\n"
        f"> Extracted: {now}\n"
        f"> Mode: {mode} | {char_count} chars (compressed {compression} from {html_chars})\n\n"
    )
    return header + content


# ===================================================================
# Section 5: CLI
# ===================================================================

async def run(args: argparse.Namespace) -> str:
    """Main async entry point."""
    target = args.target
    is_url = target.startswith("http://") or target.startswith("https://")
    is_file = not is_url and Path(target).exists()

    if not is_url and not is_file:
        print(f"ERROR: '{target}' is not a valid URL or existing file path.", file=sys.stderr)
        sys.exit(1)

    base_url = target if is_url else ""

    # Load page
    if is_file:
        html, title = load_local_file(target)
    elif args.no_js:
        html, title = load_page_static(target, timeout=args.timeout // 1000)
    else:
        html, title = await load_page_playwright(
            target, timeout=args.timeout, wait_selector=args.wait_selector
        )

    html_chars = len(html)

    if not _HAS_BS4:
        print("ERROR: beautifulsoup4 is required. Install with: pip install beautifulsoup4",
              file=sys.stderr)
        sys.exit(1)

    soup = _get_soup(html)

    # Detect or override mode
    if args.mode == "auto":
        mode = detect_page_type(soup)
    else:
        mode = args.mode

    # Extract content
    if mode == "interactive" and is_url and not args.no_js:
        content = await extract_interactive(
            html, target, timeout=args.timeout,
            wait_selector=args.wait_selector,
            include_nav=args.include_nav,
            include_forms=args.include_forms,
        )
    elif mode == "table":
        content = extract_tables(html, base_url)
    else:
        content = extract_article(
            html, base_url,
            include_nav=args.include_nav,
            include_forms=args.include_forms,
        )

    if not title:
        title = urlparse(target).netloc if is_url else Path(target).stem

    output = format_output(
        content=content,
        title=title,
        url=target,
        mode=mode,
        html_chars=html_chars,
        max_chars=args.max_chars,
        as_json=args.json,
    )

    return output


def main():
    parser = argparse.ArgumentParser(
        description="Semantic Snapshot — extract clean structured content from web pages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("target", help="URL or local HTML file path")
    parser.add_argument("--mode", choices=["auto", "article", "interactive", "table"],
                        default="auto", help="Page type detection mode (default: auto)")
    parser.add_argument("--max-chars", type=int, default=8000,
                        help="Truncate output at N chars (default: 8000)")
    parser.add_argument("--include-nav", action="store_true",
                        help="Include navigation elements")
    parser.add_argument("--include-forms", action="store_true",
                        help="Include form elements")
    parser.add_argument("--output", type=str, default=None,
                        help="Write to file instead of stdout")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON with metadata")
    parser.add_argument("--wait-selector", type=str, default=None,
                        help="Wait for CSS selector before extracting")
    parser.add_argument("--timeout", type=int, default=15000,
                        help="Page load timeout in ms (default: 15000)")
    parser.add_argument("--no-js", action="store_true",
                        help="Use requests+bs4 instead of Playwright")

    args = parser.parse_args()

    try:
        result = asyncio.run(run(args))
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        sys.exit(1)

    if args.output:
        Path(args.output).write_text(result, encoding="utf-8")
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(result)


if __name__ == "__main__":
    main()
