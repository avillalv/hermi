import { fireEvent, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, expect, test, vi } from "vitest"
import { authStore } from "../auth/authStore"
import { bodyOf, mockApi, reset, show } from "../onboarding/testing"
import { TripGroup } from "../trips/TripGroup"
import { InviteLanding } from "./InviteLanding"

const ana = { id: "p1", name: "Ana", color: "#FF5E7E", home_airports: [], linked_user_id: "u1", is_me: true }
const sam = { id: "p2", name: "Sam", color: "#FFCB2E", home_airports: [], linked_user_id: null, is_me: false }
const trip = (over: Record<string, unknown> = {}) => ({
  id: "t1", version: 1, name: "Lisbon", status: "planning", start_date: null, end_date: null,
  home_currency: "USD", my_role: "owner", destinations: [], travelers: [ana, sam], editors_can_invite: false, ...over,
})
const members = [
  { user_id: "u1", display_name: "Ana", role: "owner", person_id: "p1", joined_at: "2026-01-01T00:00:00Z" },
  { user_id: "u2", display_name: "Sam", role: "editor", person_id: null, joined_at: "2026-01-02T00:00:00Z" },
]
const pending = { id: "i1", role: "viewer", email: "kim@example.com", url: null, uses_left: 1, expires_at: "2026-02-01T00:00:00Z", created_at: "2026-01-01T00:00:00Z", status: "pending" }
const ent = { limits: { collaborators: 1 }, trip_passes: [] }
const isGet = (i?: RequestInit) => !i?.method || i.method === "GET"
const posted = (f: ReturnType<typeof mockApi>) => {
  const c = f.mock.calls.find(([u, i]) => String(u).endsWith("/invites") && (i as RequestInit | undefined)?.method === "POST")
  return c ? JSON.parse(String((c[1] as RequestInit).body)) : undefined
}
const called = (f: ReturnType<typeof mockApi>, method: string, suffix: string) =>
  f.mock.calls.some(([u, i]) => String(u).endsWith(suffix) && (i as RequestInit | undefined)?.method === method)
type Over = { trip?: unknown; invites?: unknown[]; post?: () => Response }
const api = (o: Over = {}) => (u: string, i?: RequestInit) => {
  if (u.endsWith("/v1/trips/t1") && isGet(i)) return Response.json(o.trip ?? trip())
  if (u.endsWith("/v1/trips/t1/members") && isGet(i)) return Response.json(members)
  if (u.endsWith("/v1/trips/t1/invites") && isGet(i)) return Response.json(o.invites ?? [])
  if (u.endsWith("/v1/me/entitlements")) return Response.json(ent)
  if (i?.method === "POST" && u.endsWith("/invites"))
    return o.post?.() ?? Response.json({ ...pending, id: "i2", email: null, url: "https://hermi.world/invite/abc" }, { status: 201 })
  if (i?.method === "POST" && u.endsWith("/share-links")) return Response.json({ id: "s1", url: "https://hermi.world/s/xyz" }, { status: 201 })
  if (i?.method === "PATCH") return Response.json(members[1])
  if (i?.method === "DELETE") return new Response(null, { status: 204 })
  return undefined
}
const open = (query = "") => show(<TripGroup />, "/trips/:id/group", `/trips/t1/group${query}`)
const events: string[] = []
const listen = (e: Event) => events.push((e as CustomEvent).detail.event)
const online = (on: boolean, extra: object = {}) => vi.stubGlobal("navigator", { ...navigator, onLine: on, share: undefined, ...extra })

beforeEach(() => {
  reset("free")
  sessionStorage.removeItem("hermi.invite")
  events.length = 0
  window.addEventListener("hermi:event", listen)
})
afterEach(() => {
  window.removeEventListener("hermi:event", listen)
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

test("members block lists roles and the count under Invite", async () => {
  mockApi(api())
  open()
  expect(await screen.findByRole("group", { name: "Sam, editor" })).toBeInTheDocument()
  expect(await screen.findByText("1 of 1 collaborators")).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Invite" })).toBeEnabled()
})

test("loading shows a members skeleton", async () => {
  mockApi((u, i) => (u.endsWith("/members") ? (new Promise(() => {}) as never) : api()(u, i)))
  open()
  expect(await screen.findByRole("status", { name: "Loading" })).toBeInTheDocument()
})

test("a members error offers retry", async () => {
  mockApi((u, i) => (u.endsWith("/members") ? new Response("{}", { status: 500 }) : api()(u, i)))
  open()
  expect(await screen.findByText("We could not load members. Try again.", {}, { timeout: 3000 })).toBeInTheDocument()
})

test("owner changes a role and removes a member", async () => {
  const f = mockApi(api())
  open()
  fireEvent.change(await screen.findByLabelText("Role for Sam"), { target: { value: "viewer" } })
  await waitFor(() => expect(bodyOf(f, "/members/u2")).toEqual({ role: "viewer" }))
  fireEvent.click(screen.getByRole("button", { name: "Remove member Sam" }))
  await waitFor(() => expect(called(f, "DELETE", "/members/u2")).toBe(true))
})

test("the sheet has the role radio group and the free line, and shares through the clipboard fallback", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined)
  online(true, { clipboard: { writeText } })
  const f = mockApi(api())
  open()
  fireEvent.click(await screen.findByRole("button", { name: "Invite" }))
  expect(screen.getByRole("radiogroup", { name: "Role" })).toBeInTheDocument()
  expect(screen.getByLabelText("Editor")).toBeChecked()
  expect(screen.getByText("They join free. You share your trip's features with them on this trip.")).toBeInTheDocument()
  fireEvent.click(screen.getByLabelText("Viewer"))
  fireEvent.click(screen.getByRole("button", { name: "Share invite link" }))
  await waitFor(() => expect(writeText).toHaveBeenCalledWith("https://hermi.world/invite/abc"))
  expect(posted(f)).toEqual({ role: "viewer" })
  expect(await screen.findByText("Link copied. Paste it into a message.")).toBeInTheDocument()
  expect(events).toEqual(expect.arrayContaining(["invite_sheet_opened", "invite_sent"]))
})

test("navigator.share is used when present", async () => {
  const share = vi.fn().mockResolvedValue(undefined)
  online(true, { share })
  mockApi(api())
  open("?invite=1")
  fireEvent.click(await screen.findByRole("button", { name: "Share invite link" }))
  await waitFor(() => expect(share).toHaveBeenCalled())
})

test("an email invite validates, posts the email, and a pending invite can be revoked", async () => {
  online(true, { clipboard: { writeText: vi.fn().mockResolvedValue(undefined) } })
  const f = mockApi(api({ invites: [pending] }))
  open("?invite=1")
  const field = await screen.findByLabelText("Email")
  fireEvent.click(screen.getByRole("button", { name: "Create invite" }))
  expect(await screen.findByText("Enter a valid email address.")).toBeInTheDocument()
  fireEvent.change(field, { target: { value: "lee@example.com" } })
  fireEvent.click(screen.getByRole("button", { name: "Create invite" }))
  await waitFor(() => expect(posted(f)).toEqual({ role: "editor", email: "lee@example.com" }))
  expect(await screen.findByText(/kim@example.com, viewer, expires/)).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Resend invite to kim@example.com" })).toBeInTheDocument()
  fireEvent.click(screen.getByRole("button", { name: "Revoke invite for kim@example.com" }))
  await waitFor(() => expect(called(f, "DELETE", "/invites/i1")).toBe(true))
})

test.each([
  [500, {}, "We could not create the link. Try again."],
  [429, { detail: "This trip has 20 open invites. Revoke one first." }, "You have 20 pending invites. Cancel one to send another."],
  [402, { detail: "cap" }, "This trip has 6 collaborators. Remove one to invite someone else."],
])("create failure %s shows its message", async (status, body, text) => {
  mockApi(api({ post: () => Response.json(body, { status }) }))
  open("?invite=1")
  fireEvent.click(await screen.findByRole("button", { name: "Share invite link" }))
  expect(await screen.findByRole("alert")).toHaveTextContent(text)
})

test("a 402 with a paywall hint shows the invite paywall with a close control and the free paths", async () => {
  online(true, { clipboard: { writeText: vi.fn().mockResolvedValue(undefined) } })
  const f = mockApi(api({ post: () => Response.json({ detail: "x", paywall: { trigger: "invite" } }, { status: 402 }) }))
  open("?invite=1")
  fireEvent.click(await screen.findByRole("button", { name: "Share invite link" }))
  expect(await screen.findByText("Plan together. They join free.")).toBeInTheDocument()
  expect(screen.getByRole("link", { name: "See Trip Pass and Plus" })).toHaveAttribute("href", "/account")
  fireEvent.click(screen.getByRole("button", { name: "Share a read-only link" }))
  await waitFor(() => expect(called(f, "POST", "/share-links")).toBe(true))
  fireEvent.click(screen.getByRole("button", { name: "Keep my one collaborator" }))
  expect(screen.queryByText("Plan together. They join free.")).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole("button", { name: "Close" }))
  expect(screen.queryByRole("region", { name: "Invite people" })).not.toBeInTheDocument()
})

test("offline disables sending and says Connect to send an invite.", async () => {
  online(false)
  mockApi(api())
  open("?invite=1")
  expect(await screen.findByText("Connect to send an invite.")).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Share invite link" })).toBeDisabled()
})

test("an editor without permission sees no Invite button and the owner's name", async () => {
  mockApi(api({ trip: trip({ my_role: "editor" }) }))
  open()
  expect(await screen.findByText("Only Ana can invite people.")).toBeInTheDocument()
  expect(screen.queryByRole("button", { name: "Invite" })).not.toBeInTheDocument()
})

test("an editor allowed to invite can only pick Viewer", async () => {
  mockApi(api({ trip: trip({ my_role: "editor", editors_can_invite: true }) }))
  open("?invite=1")
  expect(await screen.findByLabelText("Viewer")).toBeChecked()
  expect(screen.queryByLabelText("Editor")).not.toBeInTheDocument()
})

// --- landing ---
const preview = { trip_name: "Lisbon", cover_url: null, inviter_name: "Sam", role: "editor" }
const land = () => show(<InviteLanding />, "/invite/:token", "/invite/abc")
const landApi = (accept?: () => Response) => (u: string, i?: RequestInit) => {
  if (u.endsWith("/v1/invites/abc") && isGet(i)) return Response.json(preview)
  if (u.endsWith("/v1/invites/abc/accept")) return accept?.() ?? Response.json(trip({ id: "t9", travelers: [ana] }))
  return undefined
}

test("landing shows who invited you and to which trip with no sign-in, and Join sends you to sign in", async () => {
  authStore.signOut()
  mockApi(landApi())
  land()
  expect(await screen.findByRole("heading", { name: "Sam invited you to Lisbon" })).toBeInTheDocument()
  expect(events).toContain("invite_opened")
  fireEvent.click(screen.getByRole("button", { name: "Join trip" }))
  expect(sessionStorage.getItem("hermi.invite")).toBe("abc")
  expect(screen.getByTestId("where")).toHaveTextContent("/sign-in")
})

test("joining opens the trip", async () => {
  mockApi(landApi())
  land()
  fireEvent.click(await screen.findByRole("button", { name: "Join trip" }))
  await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/trips/t9"))
  expect(events).toContain("invite_accepted")
})

test("after joining, unclaimed travelers are offered and None of these goes on", async () => {
  mockApi(landApi(() => Response.json(trip({ id: "t9", travelers: [sam] }))))
  land()
  fireEvent.click(await screen.findByRole("button", { name: "Join trip" }))
  expect(await screen.findByText("You were added by Sam")).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Sam" })).toBeInTheDocument()
  fireEvent.click(screen.getByRole("button", { name: "None of these" }))
  await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/trips/t9"))
})

test("an already-member invite opens the trip", async () => {
  mockApi(landApi(() => Response.json({ detail: "x", trip_id: "t7" }, { status: 409 })))
  land()
  fireEvent.click(await screen.findByRole("button", { name: "Join trip" }))
  await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/trips/t7"))
})

test("landing loading shows the shared skeleton", async () => {
  mockApi(() => new Promise(() => {}) as never)
  land()
  expect(await screen.findByRole("status", { name: "Loading" })).toBeInTheDocument()
})

test("an expired, used or revoked invite says it is no longer valid", async () => {
  mockApi(() => Response.json({ detail: "gone" }, { status: 410 }))
  land()
  expect(await screen.findByRole("alert")).toHaveTextContent("This invite is no longer valid.")
  expect(screen.queryByRole("button", { name: "Join trip" })).not.toBeInTheDocument()
})

test("landing load error offers retry, and offline disables Join", async () => {
  mockApi(() => new Response("{}", { status: 500 }))
  const { unmount } = land()
  expect(await screen.findByRole("alert", {}, { timeout: 3000 })).toHaveTextContent("We could not load this invite. Try again.")
  unmount()
  online(false)
  mockApi(landApi())
  land()
  expect(await screen.findByRole("button", { name: "Join trip" })).toBeDisabled()
  expect(screen.getByText("Connect to join this trip.")).toBeInTheDocument()
})

// --- review round 1 ---
test("a role change says so politely, and a removal is sent", async () => {
  const f = mockApi(api())
  open()
  fireEvent.change(await screen.findByLabelText("Role for Sam"), { target: { value: "viewer" } })
  expect(await screen.findByRole("status")).toHaveTextContent("Sam is now a viewer")
  fireEvent.click(screen.getByRole("button", { name: "Remove member Sam" }))
  await waitFor(() => expect(f.mock.calls.some(([u, i]) => String(u).includes("/members/") && (i as RequestInit | undefined)?.method === "DELETE")).toBe(true))
})

test("the owner can make an editor the owner", async () => {
  const f = mockApi(api())
  open()
  fireEvent.click(await screen.findByRole("button", { name: "Make owner Sam" }))
  await waitFor(() => expect(called(f, "POST", "/trips/t1/transfer")).toBe(true))
  const c = f.mock.calls.find(([u]) => String(u).endsWith("/transfer"))
  expect(JSON.parse(String((c?.[1] as RequestInit).body))).toEqual({ new_owner_id: "u2" })
})

test("a non-owner confirms, then leaves the trip and goes to Trips", async () => {
  const f = mockApi((u, i) => (u.endsWith("/leave") ? new Response(null, { status: 204 }) : api({ trip: trip({ my_role: "editor" }) })(u, i)))
  open()
  fireEvent.click(await screen.findByRole("button", { name: "Leave trip" }))
  expect(called(f, "POST", "/leave")).toBe(false)
  fireEvent.click(screen.getByRole("button", { name: "Yes, leave" }))
  await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent(/^\/$/))
  expect(called(f, "POST", "/leave")).toBe(true)
})

test("a failed traveler link on the landing page shows an error", async () => {
  mockApi((u, i) => (u.includes("/members/me/traveler") ? new Response("{}", { status: 500 }) : landApi(() => Response.json(trip({ id: "t9", travelers: [sam] })))(u, i)))
  land()
  fireEvent.click(await screen.findByRole("button", { name: "Join trip" }))
  fireEvent.click(await screen.findByRole("button", { name: "Sam" }))
  expect(await screen.findByRole("alert")).toHaveTextContent("We could not join this trip. Try again.")
})

test("a signed-in person with no account is sent to onboarding before the invite is accepted", async () => {
  authStore.signIn("tok") // no persona, not onboarded
  const f = mockApi((u, i) => (u.endsWith("/v1/me") ? new Response("{}", { status: 401 }) : landApi()(u, i)))
  land()
  const join = await screen.findByRole("button", { name: "Join trip" })
  await waitFor(() => expect(join).toBeEnabled())
  fireEvent.click(join)
  await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/onboarding"))
  expect(called(f, "POST", "/accept")).toBe(false)
  expect(sessionStorage.getItem("hermi.invite")).toBe("abc")
})

test("the Invite sheet shows the Free slot count with the free path in view", async () => {
  mockApi(api())
  open("?invite=1")
  expect(await screen.findByText("1 of 1 on Free")).toBeInTheDocument()
  expect(screen.getByText(/They join free/)).toBeInTheDocument()
})

test("a trip over its collaborator limit tells the owner extras are viewers and nothing is deleted", async () => {
  mockApi(api({ trip: trip({ limited: true }) }))
  open()
  expect(await screen.findByText(/nothing is deleted/)).toBeInTheDocument()
})

test("a collaborator does not see the lapse banner", async () => {
  mockApi(api({ trip: trip({ limited: true, my_role: "viewer" }) }))
  open()
  await screen.findByRole("group", { name: "Sam, editor" })
  expect(screen.queryByText(/nothing is deleted/)).not.toBeInTheDocument()
})
