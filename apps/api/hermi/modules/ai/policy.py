"""AI policy constants. Airbnb, Vrbo and Booking.com pages are never fetched (06 section 2.4).

`BLOCKED_HOSTS` is the one list. It is a code constant: no setting, flag or admin screen changes
it. The API `blocked_domains` list and the CLI `--disallowedTools` rules are generated from it,
never typed twice.
"""

from collections.abc import Iterator

BLOCKED_HOSTS: tuple[str, ...] = ("airbnb", "vrbo", "booking")

# Second-level labels of country domains, as in airbnb.co.uk or airbnb.com.au.
_COUNTRY_SECOND_LEVELS = frozenset({"co", "com", "net", "org", "ne", "or"})

# Endings in use, for the API list only (the API takes plain hostnames, no wildcards). The match
# itself accepts any ending, so the list never limits what is refused.
_API_ENDINGS: dict[str, tuple[str, ...]] = {
    "airbnb": ("com", "ca", "co.uk", "com.au", "de", "es", "fr", "it", "co.nz", "com.br"),
    "vrbo": ("com",),
    "booking": ("com",),
}

# Always denied to the CLI web fetcher besides the brands.
_CLI_EXTRA_HOSTS = ("localhost", "127.0.0.1", "169.254.169.254")


def blocked_domain(host: str) -> str | None:
    """The blocked brand a host belongs to, or None.

    The registrable-domain label must equal a brand, with any ending (one label, or a country pair
    such as `co.uk`) and any subdomain. `notairbnb.com` and `booking.aa.com` are not matched.
    """
    labels = host.strip().lower().rstrip(".").split(".")
    for brand in BLOCKED_HOSTS:
        if brand not in labels[:-1]:
            continue
        suffix = labels[len(labels) - labels[::-1].index(brand) :]
        if len(suffix) == 1 or (len(suffix) == 2 and suffix[0] in _COUNTRY_SECOND_LEVELS):
            return brand
    return None


def api_blocked_domains() -> list[str]:
    """Hostnames for the API `blocked_domains`: bare and `www` for each ending in use."""
    return [
        f"{prefix}{brand}.{ending}"
        for brand in BLOCKED_HOSTS
        for ending in _API_ENDINGS[brand]
        for prefix in ("", "www.")
    ]


def _cli_forms() -> Iterator[str]:
    for brand in BLOCKED_HOSTS:
        # The CLI matches whole hosts and `*` is one label, so `.*.*` covers endings like `.co.kr`.
        yield from (f"{brand}.*", f"{brand}.*.*", f"*.{brand}.*", f"*.{brand}.*.*")
    yield from _CLI_EXTRA_HOSTS


def cli_disallowed_tools() -> list[str]:
    """`--disallowedTools` rules for the claude_cli provider (the stream check stays a backstop)."""
    return [f"WebFetch(domain:{form})" for form in _cli_forms()]
