# ruff: noqa: E501  (plain-sentence copy)
"""Paywall triggers and their mute caps (07 sections 6.2 and 6.5, 04 section 2.2).

One row per trigger: the PaywallHint `reason`, the free path shown beside the offer, and the caps the frequency logic reads.
Mirrored by `packages/shared/src/entitlements.ts` (a test keeps the two in step).
"""

from dataclasses import dataclass

VIEWS_PER_WEEK = 3  # paywall views per rolling 7 days, across the triggers that count
MUTE_AFTER_DISMISSALS = 3  # the same trigger dismissed this many times gets the long mute


@dataclass(frozen=True)
class Trigger:
    reason: str  # 04 PaywallHint["reason"]; the three client-initiated triggers send their own code
    free_path: str
    mute_days: int = 7  # one dismissal mutes this trigger
    long_mute_days: int = 30  # after MUTE_AFTER_DISMISSALS dismissals
    counts_toward_cap: bool = True  # counts toward VIEWS_PER_WEEK
    modal: bool = True  # false: a soft line or card, never a modal
    cooldown_days: int | None = None  # at most one per trip per this many days
    per_trip_days: int | None = None  # the offer shows at most once per trip per this many days


TRIGGERS: dict[str, Trigger] = {
    "third_trip": Trigger("trip_limit", "Archive a trip or join trips other people plan"),
    "second_route": Trigger("live_routes", "Keep one route"),
    "track_live": Trigger("live_routes", "Use 1 credit or cached fares"),
    "alert_limit": Trigger("live_routes", "Keep the cached-fare alert"),
    "invite": Trigger("sharing", "Keep the one collaborator, or share a read-only link"),
    "out_of_credits_draft": Trigger("credits", "Plan manually, or invite a friend for credits"),
    "out_of_credits_research": Trigger("credits", "Skip, or invite a friend for credits"),
    "out_of_credits_agent": Trigger("credits", "Use a research question"),
    "out_of_credits_verify": Trigger(
        "credits", "Check fewer items, or invite a friend for credits"
    ),
    "export_footer": Trigger(
        "export_footer", "Export with footer", mute_days=30, counts_toward_cap=False, modal=False
    ),
    "ninth_stay": Trigger("ninth_stay", "Save it to the later list", per_trip_days=7),
    "lifecycle_14d": Trigger(
        "lifecycle_14d",
        "Dismiss",
        mute_days=30,
        counts_toward_cap=False,
        modal=False,
        cooldown_days=14,
    ),
}
