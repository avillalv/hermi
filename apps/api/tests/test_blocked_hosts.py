"""BLOCKED_HOSTS: Airbnb, Vrbo and Booking.com are never fetched (non-negotiable rule 3)."""

import pytest

from hermi.modules.ai import policy
from hermi.modules.ai.policy import (
    BLOCKED_HOSTS,
    api_blocked_domains,
    blocked_domain,
    cli_disallowed_tools,
)
from hermi.security import ssrf


def test_constant_is_the_three_brands() -> None:
    assert BLOCKED_HOSTS == ("airbnb", "vrbo", "booking")


@pytest.mark.parametrize(
    ("host", "brand"),
    [
        ("airbnb.co.kr", "airbnb"),
        ("www.airbnb.co.uk", "airbnb"),
        ("vrbo.com", "vrbo"),
        ("secure.booking.com", "booking"),
        ("fr.airbnb.ca", "airbnb"),
        ("AIRBNB.com.", "airbnb"),
        ("a.b.airbnb.com.au", "airbnb"),
    ],
)
def test_refused(host: str, brand: str) -> None:
    assert blocked_domain(host) == brand
    assert ssrf.is_blocked_host(host)


@pytest.mark.parametrize(
    "host",
    [
        "notairbnb.com",
        "airbnbx.com",
        "booking.flyfrontier.com",
        "booking.aa.com",
        "www.kayak.com",
        "example.com",
        "airbnb",
        "evil.com.airbnb.example.com",
    ],
)
def test_lookalikes_allowed(host: str) -> None:
    assert blocked_domain(host) is None
    assert not ssrf.is_blocked_host(host)


def test_path_containing_brand_is_not_a_host_match() -> None:
    assert ssrf.url_blocked("https://example.com/airbnb.com/room") is None
    assert ssrf.url_blocked("https://www.airbnb.co.uk/rooms/1") == "airbnb"
    assert ssrf.url_blocked("not a url") is None


def test_api_list_generated_and_under_limit() -> None:
    hosts = api_blocked_domains()
    assert len(hosts) < 64 and len(set(hosts)) == len(hosts)
    for h in ("airbnb.com", "www.airbnb.co.uk", "vrbo.com", "www.vrbo.com", "booking.com"):
        assert h in hosts
    assert all(blocked_domain(h) for h in hosts)
    assert not any("*" in h for h in hosts)


def test_cli_rules_four_forms_per_brand() -> None:
    rules = cli_disallowed_tools()
    for brand in BLOCKED_HOSTS:
        for form in (f"{brand}.*", f"{brand}.*.*", f"*.{brand}.*", f"*.{brand}.*.*"):
            assert f"WebFetch(domain:{form})" in rules
    for extra in ("localhost", "127.0.0.1", "169.254.169.254"):
        assert f"WebFetch(domain:{extra})" in rules


def test_no_setting_can_change_it() -> None:
    assert isinstance(BLOCKED_HOSTS, tuple)
    src = open(policy.__file__, encoding="utf-8").read()
    assert "settings" not in src and "environ" not in src
