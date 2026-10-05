"""User-initiated link preview (10 section 2.5). Fetches through the SSRF guard, parses text/html
only and reads og:title, og:image (a URL, never fetched here), og:description and <title>."""

from dataclasses import dataclass
from html.parser import HTMLParser

from hermi.providers import ProviderError
from hermi.providers.pinned_http import PinnedHttpTransport
from hermi.security.ssrf import LINK_PREVIEW_POLICY, SsrfGuard, SsrfRefused, Transport

BLOCKED_MESSAGE = "Paste the details or use the bookmarklet."
_MAX_TEXT = 500


@dataclass(frozen=True)
class LinkPreview:
    url: str
    title: str | None = None
    description: str | None = None
    image_url: str | None = None
    blocked: bool = False
    message: str | None = None


class _Meta(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.og: dict[str, str] = {}
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title" and not self.title:
            self._in_title = True
        elif tag == "meta":
            prop = (a.get("property") or a.get("name") or "").lower()
            if prop in ("og:title", "og:image", "og:description") and a.get("content"):
                self.og.setdefault(prop, a["content"])

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def _clean(text: str | None) -> str | None:
    text = " ".join((text or "").split())[:_MAX_TEXT]
    return text or None


def _image(url: str | None) -> str | None:
    return url if url and url.startswith(("https://", "http://")) and len(url) <= 2048 else None


def parse_html(url: str, body: bytes) -> LinkPreview:
    parser = _Meta()
    parser.feed(body.decode("utf-8", errors="replace"))
    parser.close()
    return LinkPreview(
        url=url,
        title=_clean(parser.og.get("og:title") or parser.title),
        description=_clean(parser.og.get("og:description")),
        image_url=_image(parser.og.get("og:image")),
    )


def fetch_link_preview(
    url: str, *, guard: SsrfGuard | None = None, transport: Transport | None = None
) -> LinkPreview:
    guard = guard or SsrfGuard(LINK_PREVIEW_POLICY, transport or PinnedHttpTransport())
    try:
        result = guard.fetch(url)
    except SsrfRefused as exc:
        if exc.blocked_brand:
            return LinkPreview(url=url, blocked=True, message=BLOCKED_MESSAGE)
        raise ProviderError(f"link preview refused: {exc.reason}") from exc
    if result.status != 200:
        raise ProviderError(f"link preview status {result.status}", status_code=result.status)
    if result.content_type.split(";")[0].strip().lower() != "text/html":
        raise ProviderError("link preview is not html")
    return parse_html(result.url, result.body)
