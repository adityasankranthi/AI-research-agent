import httpx

from research_agent.fetch import fetch_page


class _FakeResponse:
    def __init__(self, text="", status_code=200, content_type="text/html"):
        self.text = text
        self.status_code = status_code
        self.headers = {"content-type": content_type}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("bad status", request=None, response=self)


def test_fetch_page_extracts_visible_text_and_strips_boilerplate_tags(monkeypatch):
    html = (
        "<html><head><script>var x = 1;</script><style>.a{}</style></head>"
        "<body><nav>Home</nav><header>Site</header>"
        "<p>The actual article content.</p>"
        "<footer>Copyright</footer></body></html>"
    )
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse(text=html))

    result = fetch_page("http://example.com")

    assert result.ok
    assert "actual article content" in result.text
    assert "Home" not in result.text
    assert "Site" not in result.text
    assert "Copyright" not in result.text
    assert "var x" not in result.text


def test_fetch_page_rejects_non_html_content_type(monkeypatch):
    monkeypatch.setattr(
        httpx, "get", lambda *a, **k: _FakeResponse(text="{}", content_type="application/json")
    )

    result = fetch_page("http://example.com/data.json")

    assert not result.ok
    assert result.error == "unsupported content-type"


def test_fetch_page_returns_not_ok_on_http_error_without_raising(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse(status_code=404))

    result = fetch_page("http://example.com/missing")

    assert not result.ok
    assert result.error


def test_fetch_page_truncates_to_max_chars(monkeypatch):
    html = f"<html><body><p>{'word ' * 2000}</p></body></html>"
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse(text=html))

    result = fetch_page("http://example.com", max_chars=50)

    assert result.ok
    assert len(result.text) == 50


def test_fetch_page_returns_not_ok_when_no_extractable_text(monkeypatch):
    html = "<html><body><script>only script content</script></body></html>"
    monkeypatch.setattr(httpx, "get", lambda *a, **k: _FakeResponse(text=html))

    result = fetch_page("http://example.com/empty")

    assert not result.ok
    assert result.error == "no extractable text"
