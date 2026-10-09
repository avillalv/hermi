# ruff: noqa: E501
"""Email templates (WF-047). One entry per notification kind that can be mailed.

The producing job writes the title and body of the notification row (the in-app inbox shows the same words). A template adds
the fixed parts: the button label, the one fixed sentence some kinds must carry, and the footer with the unsubscribe link.
Copy follows the brand voice: calm, specific, honest, sentence case, plain verbs, no hype, no dashes.
"""

from dataclasses import dataclass
from html import escape


@dataclass(frozen=True)
class Kind:
    category: str  # "transactional" or "marketing"; marketing needs the marketing_email consent
    cta: str  # the button label
    note: str = ""  # a fixed sentence under the body
    urgent: bool = False  # sent at once: ignores quiet hours and the unsubscribe-from-all switch
    link2: tuple[str, str] | None = None  # a fixed second link: (label, url)


CANCEL_URL = "https://apps.apple.com/account/subscriptions"
# The postal address CAN-SPAM wants in the footer of marketing mail. Owner-pending: empty until the owner supplies it, and
# while it is empty marketing mail is dropped (service.deliver_email skips it).
POSTAL_ADDRESS = ""

KINDS: dict[str, Kind] = {
    "trip_invite": Kind("transactional", "Open the trip"),
    "invite_accepted": Kind("transactional", "Open the trip"),
    "price_drop": Kind("transactional", "See the fare", "Fares change often. Check the price on the airline's own page before you book."),
    "booked_fare_drop": Kind("transactional", "Open the trip", "Check the airline's change and credit rules. A lower fare does not mean a refund or a free change."),
    "run_finished": Kind("transactional", "See the results"),
    "import_finished": Kind("transactional", "Check what we found"),
    "verify_finished": Kind("transactional", "See the results"),
    "calendar_changes": Kind("transactional", "Review the changes", "Nothing changes in your trip until you confirm."),
    "calendar_poll_stopped": Kind("transactional", "Open the trip"),
    "referral_reward": Kind("transactional", "See your credits"),
    "pre_trip_reminder": Kind("transactional", "Open the checklist"),
    "activity_digest": Kind("transactional", "See what changed"),
    "trial_ending": Kind("transactional", "Manage your plan", "You can cancel before then in your Apple subscription settings.", link2=("Cancel subscription", CANCEL_URL)),
    "account_deleted": Kind("transactional", "", "", urgent=True),
    "lifecycle": Kind("marketing", "Open Hermi"),
}

# Email clients ignore CSS variables, so these are the light-mode values of --tp-ink, --tp-ink-soft and --tp-brand (design/tokens.css).
INK, INK_SOFT, BRAND = "#17324A", "#4A6580", "#0B6BC0"

FOOTER_TRANSACTIONAL = "You get this email because of your Hermi account."
FOOTER_MARKETING = "You get this email because you chose to hear from Hermi."
UNSUB_TRANSACTIONAL = "Stop all email from Hermi"
UNSUB_MARKETING = "Unsubscribe"


def category(kind: str) -> str:
    return KINDS[kind].category


def _link(base_url: str, payload: dict) -> str | None:
    """The in-app deep link in the payload, as an absolute web URL. Only same-site paths are followed."""
    url = payload.get("url")
    if isinstance(url, str) and url.startswith("/") and not url.startswith("//"):
        return base_url.rstrip("/") + url
    return None


def render(kind: str, *, title: str, body: str, payload: dict, base_url: str, unsubscribe_url: str) -> tuple[str, str, str]:
    """(subject, text, html). Every user-provided string is escaped in the HTML."""
    k = KINDS[kind]
    link = _link(base_url, payload) if k.cta else None
    marketing = k.category == "marketing"
    footer = FOOTER_MARKETING if marketing else FOOTER_TRANSACTIONAL
    unsub_label = UNSUB_MARKETING if marketing else UNSUB_TRANSACTIONAL

    text = [title, ""]
    if body:
        text += [body, ""]
    if k.note:
        text += [k.note, ""]
    if link:
        text += [f"{k.cta}: {link}", ""]
    if k.link2:
        text += [f"{k.link2[0]}: {k.link2[1]}", ""]
    if kind != "account_deleted":
        text += [footer, f"{unsub_label}: {unsubscribe_url}"]
        if marketing and POSTAL_ADDRESS:
            text += [POSTAL_ADDRESS]

    parts = [f'<h1 style="font-size:20px;margin:0 0 12px">{escape(title)}</h1>']
    if body:
        parts.append(f'<p style="margin:0 0 12px">{escape(body)}</p>')
    if k.note:
        parts.append(f'<p style="margin:0 0 12px;color:{INK_SOFT}">{escape(k.note)}</p>')
    if link:
        parts.append(f'<p style="margin:16px 0"><a href="{escape(link, quote=True)}" style="background:{BRAND};color:#FFFFFF;padding:10px 18px;border-radius:999px;text-decoration:none">{escape(k.cta)}</a></p>')
    if k.link2:
        parts.append(f'<p style="margin:0 0 12px"><a href="{escape(k.link2[1], quote=True)}">{escape(k.link2[0])}</a></p>')
    if kind != "account_deleted":
        address = f"<br>{escape(POSTAL_ADDRESS)}" if marketing and POSTAL_ADDRESS else ""
        parts.append(f'<p style="margin:24px 0 0;font-size:12px;color:{INK_SOFT}">{escape(footer)} <a href="{escape(unsubscribe_url, quote=True)}">{escape(unsub_label)}</a>{address}</p>')
    html = f'<div style="font-family:system-ui,sans-serif;max-width:480px;margin:0 auto;color:{INK}">' + "".join(parts) + "</div>"
    return title, "\n".join(text).rstrip() + "\n", html
