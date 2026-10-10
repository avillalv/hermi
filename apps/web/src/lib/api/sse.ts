// Server-sent events over fetch, because EventSource cannot send the bearer header (04 section 5.13).
export type SseMessage = { id: string | null; event: string; data: string }

export class SseError extends Error {
  constructor(readonly status: number) {
    super(`sse ${status}`)
  }
}

type Opts = {
  token: string | null
  /** Sent as Last-Event-ID so the server replays from the next event. */
  lastEventId?: string
  signal?: AbortSignal
  fetch?: typeof fetch
  onMessage: (m: SseMessage) => void
}

function parseFrame(raw: string): SseMessage | null {
  let id: string | null = null
  let event = "message"
  const data: string[] = []
  for (const line of raw.split("\n")) {
    if (!line || line.startsWith(":")) continue // blank, or a comment such as the heartbeat
    const i = line.indexOf(":")
    const field = i < 0 ? line : line.slice(0, i)
    const value = i < 0 ? "" : line.slice(i + 1).replace(/^ /, "")
    if (field === "id") id = value
    else if (field === "event") event = value
    else if (field === "data") data.push(value)
  }
  return data.length ? { id, event, data: data.join("\n") } : null
}

/** Opens the stream and calls `onMessage` per frame. Resolves when the server closes it; throws `SseError` on a non 2xx answer. */
export async function readSse(url: string, { token, lastEventId, signal, fetch: f, onMessage }: Opts): Promise<void> {
  const headers = new Headers({ Accept: "text/event-stream" })
  if (token) headers.set("Authorization", `Bearer ${token}`)
  if (lastEventId) headers.set("Last-Event-ID", lastEventId)
  const res = await (f ?? ((...a) => fetch(...a)))(url, { headers, signal, credentials: "omit" })
  if (!res.ok || !res.body) throw new SseError(res.status)
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buf = ""
  for (;;) {
    const { done, value } = await reader.read()
    buf += decoder.decode(value, { stream: !done }).replace(/\r\n?/g, "\n")
    let cut: number
    while ((cut = buf.indexOf("\n\n")) >= 0) {
      const m = parseFrame(buf.slice(0, cut))
      buf = buf.slice(cut + 2)
      if (m) onMessage(m)
    }
    if (done) return
  }
}
