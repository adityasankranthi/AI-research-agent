from dataclasses import dataclass

import httpx
from lxml import html as lxml_html

_STRIP_TAGS = ("script", "style", "nav", "header", "footer", "noscript")


@dataclass
class FetchResult:
    url: str
    text: str
    ok: bool
    error: str = ""


def _extract_main_text(html: str) -> str:
    tree = lxml_html.fromstring(html)
    for tag in _STRIP_TAGS:
        for element in tree.xpath(f"//{tag}"):
            element.drop_tree()
    return " ".join(tree.text_content().split())


def fetch_page(url: str, timeout: float = 15.0, max_chars: int = 4000) -> FetchResult:
    """Fetch a URL and extract its visible text. Never raises -- every failure mode
    (network error, non-HTML content, empty extraction) degrades to
    `FetchResult(ok=False)` so callers can fall back to the search snippet they
    already have instead of losing the source entirely."""
    try:
        response = httpx.get(
            url,
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "research-agent/0.1"},
        )
        response.raise_for_status()
    except httpx.HTTPError as e:
        return FetchResult(url=url, text="", ok=False, error=str(e))

    if "text/html" not in response.headers.get("content-type", ""):
        return FetchResult(url=url, text="", ok=False, error="unsupported content-type")

    try:
        text = _extract_main_text(response.text)
    except Exception as e:  # malformed markup lxml can't parse
        return FetchResult(url=url, text="", ok=False, error=str(e))

    if not text:
        return FetchResult(url=url, text="", ok=False, error="no extractable text")
    return FetchResult(url=url, text=text[:max_chars], ok=True)
