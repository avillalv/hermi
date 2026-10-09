# ruff: noqa: E501
"""One-click unsubscribe (WF-047). Public: the signed token in the link is the whole authorization, no login, no cookie.

GET shows a confirm page with one button that posts the same link; it changes nothing, so a mail scanner that opens every link
cannot unsubscribe anyone. POST changes state: the page's button, and the RFC 8058 one-click call a mail app makes for the
List-Unsubscribe-Post header.
"""

from html import escape

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from hermi import db
from hermi.errors import ApiError
from hermi.modules.notifications import service

router = APIRouter()

PAGE = (
    '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
    '<title>Hermi</title><body style="font-family:system-ui,sans-serif;max-width:480px;margin:48px auto;padding:0 16px">'
    '<h1 style="font-size:22px">{title}</h1><p>{body}</p>{form}</body>'
)
FORM = '<form method="post" action="{action}"><button type="submit" style="font:inherit;padding:10px 18px;border-radius:999px">{label}</button></form>'
COPY = {
    "all": ("Stop all email from Hermi?", "Stop all email from Hermi", "We will stop sending you email from Hermi. We will still email you about deleting your account.", "We have stopped all email from Hermi. We will still email you about deleting your account."),
    "marketing": ("Unsubscribe from marketing email?", "Unsubscribe", "We will stop sending you marketing email. Emails about your trips and account still arrive.", "We have stopped marketing email. Emails about your trips and account still arrive."),
}
BAD = "This unsubscribe link is not valid. Open the latest email from Hermi and use the link there."


def _verify(request: Request, t: str) -> tuple:
    parsed = service.verify_unsubscribe(request.app.state.settings, t)
    if parsed is None:
        raise ApiError(400, "invalid_unsubscribe_link", BAD)
    return parsed


@router.get("/unsubscribe", response_class=HTMLResponse)
def unsubscribe_page(t: str, request: Request) -> HTMLResponse:
    _, scope = _verify(request, t)
    title, label, body, _ = COPY[scope]
    action = escape(str(request.url.path) + "?t=" + t, quote=True)
    return HTMLResponse(PAGE.format(title=title, body=body, form=FORM.format(action=action, label=label)))


@router.post("/unsubscribe", response_model=None)
def unsubscribe_one_click(t: str, request: Request):
    user_id, scope = _verify(request, t)
    settings = request.app.state.settings
    with db.system_session("unsubscribe", settings=settings, route="POST /v1/unsubscribe", caller=str(user_id)) as s:
        if not service.apply_unsubscribe(s, user_id, scope):
            raise ApiError(400, "invalid_unsubscribe_link", BAD)
    if "text/html" in request.headers.get("accept", ""):  # the confirm page's button
        return HTMLResponse(PAGE.format(title="You are unsubscribed", body=COPY[scope][3], form=""))
    return {"unsubscribed": True}
