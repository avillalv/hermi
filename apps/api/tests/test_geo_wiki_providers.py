"""Geoapify and Wikipedia parsing against recorded fixtures and mocked transports. No network."""

import asyncio
import json
import logging
from pathlib import Path

import httpx
import pytest

from hermi.providers import ProviderError, geoapify, wikipedia
from hermi.providers import geoapify as geo

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _result(name: str, kind: str = "city", importance: float | None = 0.5, **extra: object) -> dict:
    return {
        "name": name,
        "result_type": kind,
        "country": "Indonesia",
        "country_code": "id",
        "state": extra.pop("state", None),
        "lat": extra.pop("lat", -8.4),
        "lon": extra.pop("lon", 115.2),
        "formatted": f"{name}, Indonesia",
        "timezone": {"name": "Asia/Makassar"},
        "rank": {"importance": importance},
        "bbox": {"lon1": 114.4, "lat1": -8.9, "lon2": 115.7, "lat2": -8.0},
        "place_id": f"pid-{name}",
        **extra,
    }


# --- Destination search ---------------------------------------------------------------------


def test_exact_names_rank_first_and_noise_is_dropped() -> None:
    results = [
        _result("Balikpapan", importance=0.9, lat=-1.2, lon=116.8),
        _result("Bali", kind="state", importance=0.6),
        _result("Bali", kind="state", importance=0.6),  # duplicate from the other endpoint
        _result("KYOT-TV", kind="amenity", importance=0.0),
        _result("Jalan Bali", kind="street"),
    ]

    suggestions = geo.merge_results("bali", results)

    assert [s.name for s in suggestions] == ["Bali", "Balikpapan"]
    bali = suggestions[0]
    assert bali.country_code == "ID"
    assert bali.timezone == "Asia/Makassar"
    assert bali.bbox == [114.4, -8.9, 115.7, -8.0]
    assert bali.region is None


def test_state_is_kept_as_region_for_cities() -> None:
    [kyoto] = geo.merge_results("kyoto", [_result("Kyoto", state="Kyoto Prefecture")])

    assert kyoto.region == "Kyoto Prefecture"


def test_search_queries_both_endpoints() -> None:
    geoapify._cache.clear()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/search"):
            return httpx.Response(200, json={"results": [_result("Bali", kind="state")]})
        return httpx.Response(500)

    async def run() -> list:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await geoapify.search_destinations("Bali", "key", client)

    assert [s.name for s in asyncio.run(run())] == ["Bali"]


def test_search_fails_only_when_both_endpoints_fail() -> None:
    geoapify._cache.clear()

    async def run() -> list:
        transport = httpx.MockTransport(lambda r: httpx.Response(401))
        async with httpx.AsyncClient(transport=transport) as client:
            return await geoapify.search_destinations("Nowhere", "bad-key", client)

    with pytest.raises(ProviderError):
        asyncio.run(run())


# --- Places ---------------------------------------------------------------------------------


def test_category_results_come_with_details() -> None:
    places = geo.parse_places(fixture("geoapify_places_museums.json"))

    shimadzu = next(p for p in places if p.name == "Shimadzu Foundation Memorial Museum")
    assert shimadzu.local_name == "島津製作所創業記念資料館"
    assert shimadzu.category == "museum"
    assert shimadzu.address is not None and shimadzu.address.startswith("Kiyamachi Street")
    assert (shimadzu.opening_hours, shimadzu.wikidata) == ("9:30-17:00", "Q11476799")
    assert shimadzu.website == "https://www.shimadzu.co.jp/visionary/memorial-hall/"
    assert shimadzu.distance_m == 242 and shimadzu.has_details


def test_places_without_an_english_name_keep_their_local_name() -> None:
    places = geo.parse_places(fixture("geoapify_places_museums.json"))

    kaleidoscope = next(p for p in places if p.name == "京都万華鏡ミュージアム")
    assert kaleidoscope.local_name is None


def test_text_results_are_basic_until_details_are_fetched() -> None:
    [kinkaku, *_] = geo.parse_geocode(fixture("geoapify_geocode_kinkaku.json"))

    assert (kinkaku.name, kinkaku.local_name) == ("Kinkaku-ji", "金閣寺")
    assert kinkaku.address == "Kita Ward, Kyoto, Kinkakuji-chō 603-8361, Japan"
    assert not kinkaku.has_details and kinkaku.website is None


def test_details_parse_like_category_results() -> None:
    place = geo.parse_details(fixture("geoapify_place_details.json"))

    assert place is not None
    assert place.name == "Honnoji Temple Treasure Hall" and place.local_name == "本能寺大寶殿宝物館"
    assert place.category == "museum" and place.has_details


@pytest.mark.parametrize(
    ("kinds", "category"),
    [
        (["catering", "catering.bar"], "nightlife"),
        (["catering.restaurant.ramen"], "food"),
        (["building.tourism", "entertainment.museum"], "museum"),
        (["leisure", "leisure.park"], "nature"),
        (["beach"], "nature"),
        (["tourism.sights.place_of_worship.temple"], "sights"),
        (["commercial.marketplace"], "shopping"),
        (["office"], "other"),
    ],
)
def test_places_sort_into_activity_categories(kinds: list[str], category: str) -> None:
    assert geo.activity_category(kinds) == category


def test_odd_osm_values_dont_sink_a_search() -> None:
    feature = fixture("geoapify_places_museums.json")["features"][0]
    phone_as_number = {**feature["properties"], "contact": {"phone": 50660072170}}
    broken = {"properties": {**feature["properties"], "place_id": "x", "lat": "not a number"}}

    places = geo.parse_places({"features": [{"properties": phone_as_number}, broken]})

    assert [p.phone for p in places] == ["50660072170"]


@pytest.mark.parametrize(
    ("status", "text"),
    [(401, "refused the API key"), (429, "credits are used up"), (500, "returned an error")],
)
def test_fetch_explains_failures(status: int, text: str) -> None:
    transport = httpx.MockTransport(lambda r: httpx.Response(status))
    with httpx.Client(transport=transport) as client, pytest.raises(ProviderError, match=text):
        geo.fetch(client, geo.PLACES_URL, {}, "key")


def test_fetch_sends_the_key_and_returns_json() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"features": []})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert geo.fetch(client, geo.PLACES_URL, {"limit": 1}, "k") == {"features": []}
    assert seen[0].url.params["apiKey"] == "k"


def test_area_searches_filter_by_country_then_box_then_circle() -> None:
    _, text = geo.text_request("ramen", 10.0, -84.0, 1000, geo.Area(country_code="CR"))
    assert text["filter"] == "countrycode:cr"
    _, boxed = geo.kind_request("museums", 10.0, -84.0, 1000, area=geo.Area(bbox=(1, 2, 3, 4)))
    assert boxed["filter"] == "rect:1,2,3,4"
    _, circle = geo.kind_request("museums", 10.0, -84.0, 1000)
    assert circle["filter"] == "circle:-84.0,10.0,1000"


# --- Wikipedia ------------------------------------------------------------------------------

WIKIDATA = {
    "entities": {"Q11476799": {"sitelinks": {"enwiki": {"title": "Shimadzu Memorial Hall"}}}}
}
ARTICLE = {
    "query": {
        "pages": [
            {
                "title": "Shimadzu Memorial Hall",
                "extract": "A museum on the history of Shimadzu Corporation.",
                "fullurl": "https://en.wikipedia.org/wiki/Shimadzu_Memorial_Hall",
                "thumbnail": {"source": "https://upload.wikimedia.org/x.jpg"},
            }
        ]
    }
}


def wiki_client(handler) -> wikipedia.WikipediaClient:
    http = httpx.Client(
        transport=httpx.MockTransport(handler),
        headers={"User-Agent": wikipedia.user_agent("tester@example.com")},
    )
    return wikipedia.WikipediaClient("tester@example.com", http)


def test_wiki_summary_comes_from_the_wikidata_link() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        body = WIKIDATA if request.url.host == "www.wikidata.org" else ARTICLE
        return httpx.Response(200, json=body)

    client = wiki_client(handler)
    title = client.english_title("Q11476799")
    article = client.article(title or "")

    assert title == "Shimadzu Memorial Hall"
    assert article is not None and article.extract.startswith("A museum")
    assert article.image_url == "https://upload.wikimedia.org/x.jpg"
    assert "tester@example.com" in seen[0].headers["user-agent"]


def test_disambiguation_and_missing_pages_are_none() -> None:
    pages = [{"title": "X", "pageprops": {"disambiguation": ""}}]
    client = wiki_client(lambda r: httpx.Response(200, json={"query": {"pages": pages}}))
    assert client.article("X") is None
    client = wiki_client(
        lambda r: httpx.Response(200, json={"query": {"pages": [{"missing": True}]}})
    )
    assert client.article("Y") is None


def test_wikipedia_http_failure_is_a_provider_error() -> None:
    with pytest.raises(ProviderError):
        wiki_client(lambda r: httpx.Response(503)).article("X")


def test_the_api_key_never_reaches_the_logs(caplog: pytest.LogCaptureFixture) -> None:
    from hermi.logging_setup import setup_logging

    setup_logging("INFO")
    transport = httpx.MockTransport(lambda r: httpx.Response(200, json={"features": []}))
    with caplog.at_level(logging.INFO), httpx.Client(transport=transport) as client:
        geo.fetch(client, geo.PLACES_URL, {}, "SECRET-KEY-123")

    assert "SECRET-KEY-123" not in "".join(r.getMessage() for r in caplog.records)
