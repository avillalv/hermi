/* global document, fetch, FormData */
// Waitlist form: posts JSON to data-api-url on <body> (default same-origin /v1/waitlist).
const form = document.getElementById("waitlist");
const note = document.getElementById("status");
const url = (document.body.dataset.apiUrl || "").replace(/\/$/, "") + "/v1/waitlist";
const say = (text, cls) => { note.textContent = text; note.className = cls; };
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = form.querySelector("button");
  btn.disabled = true;
  say("Sending...", "");
  try {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(Object.fromEntries(new FormData(form))),
    });
    if (r.ok) { form.reset(); say("You are on the list. Check your email for a confirmation.", "ok"); }
    else if (r.status === 429) say("Too many tries. Wait a minute and try again.", "err");
    else if (r.status === 422) say("Check your email address and try again.", "err");
    else say("Something went wrong. Try again in a moment.", "err");
  } catch {
    say("No connection. Try again in a moment.", "err");
  }
  btn.disabled = false;
});
