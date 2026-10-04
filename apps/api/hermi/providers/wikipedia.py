"""Wikipedia summaries and lead photos for destinations (MediaWiki Action API, no key).

Wikimedia rejects API clients whose User-Agent has no contact information, so requests
identify the app with WIKIMEDIA_CONTACT from .env.
"""

from dataclasses import dataclass
from typing import Any

import httpx

from hermi.providers import ProviderError

API_URL = "https://en.wikipedia.org/w/api.php"
WIKIDATA_URL = "https://www.wikidata.org/w/api.php"
# A standard Wikimedia thumbnail width; large enough for a hero image.
IMAGE_WIDTH = 1280
APP_NAME = "Hermi"


@dataclass(frozen=True)
class WikiArticle:
    title: str
    extract: str
    page_url: str | None
    image_url: str | None
    image_file: str | None


def user_agent(contact: str) -> str:
    return f"{APP_NAME}/1.0 (trip planner; {contact})"


class WikipediaClient:
    def __init__(self, contact: str, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(
            timeout=15, headers={"User-Agent": user_agent(contact)}
        )

    def close(self) -> None:
        self._client.close()

    def _query(self, params: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._client.get(
                API_URL, params={**params, "format": "json", "formatversion": 2}
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"Wikipedia request failed: {exc}") from exc

    def find_article(self, search: str) -> WikiArticle | None:
        """Best-matching article for a free-text search, or None (also for disambiguation pages)."""
        hits = self._query(
            {
                "action": "query",
                "list": "search",
                "srsearch": search,
                "srlimit": 1,
                "srnamespace": 0,
            }
        )
        results = hits.get("query", {}).get("search", [])
        if not results:
            return None
        return self.article(results[0]["title"])

    def english_title(self, wikidata_id: str) -> str | None:
        """The English Wikipedia title linked from a Wikidata item (OSM tags places with these)."""
        try:
            response = self._client.get(
                WIKIDATA_URL,
                params={
                    "action": "wbgetentities",
                    "ids": wikidata_id,
                    "props": "sitelinks",
                    "sitefilter": "enwiki",
                    "format": "json",
                },
            )
            response.raise_for_status()
            entity = (response.json().get("entities") or {}).get(wikidata_id) or {}
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"Wikidata request failed: {exc}") from exc
        return ((entity.get("sitelinks") or {}).get("enwiki") or {}).get("title")

    def article(self, title: str) -> WikiArticle | None:
        """The lead of an article by title, or None if it's missing or a disambiguation page."""
        data = self._query(
            {
                "action": "query",
                "prop": "extracts|pageimages|info|pageprops",
                "exintro": 1,
                "explaintext": 1,
                "exsentences": 3,
                "piprop": "thumbnail|name",
                "pithumbsize": IMAGE_WIDTH,
                "inprop": "url",
                "ppprop": "disambiguation",
                "redirects": 1,
                "titles": title,
            }
        )
        pages = data.get("query", {}).get("pages", [])
        if not pages:
            return None
        page = pages[0]
        if page.get("missing") or "disambiguation" in (page.get("pageprops") or {}):
            return None
        thumbnail = page.get("thumbnail") or {}
        return WikiArticle(
            title=page["title"],
            extract=(page.get("extract") or "").strip(),
            page_url=page.get("fullurl"),
            image_url=thumbnail.get("source"),
            image_file=page.get("pageimage"),
        )
