import { useState } from "react"
import { Btn, Icon, SegItem, SegmentedControl, TextField } from "../../components/kit"
import { t } from "../../lib/i18n"
import { toMinor } from "../../lib/money"
import { track } from "../../lib/track"
import { Modal } from "../itinerary/Modal"
import { createStay, parseLink, type StayIn } from "./api"

export type Prefill = { url: string; title: string; via: "bookmarklet" | null }

/**
 * 05 6.11 Add a stay: paste a link or add by hand (the partner search and "Paste a booking" ways are later tickets).
 * The link is sent exactly as pasted (outer whitespace aside). `parse-link` reads the URL text only, so no page is ever opened.
 */
export function AddStay({ tripId, currency, prefill, onClose, onAdded }: { tripId: string; currency: string; prefill: Prefill | null; onClose: () => void; onAdded: () => void }) {
  const [mode, setMode] = useState<"paste" | "hand">("paste")
  const [url, setUrl] = useState(prefill?.url ?? "")
  const [title, setTitle] = useState(prefill?.title ?? "")
  const [price, setPrice] = useState("")
  const [notes, setNotes] = useState("")
  const [errors, setErrors] = useState<{ url?: string; title?: string; price?: string }>({})
  const [failed, setFailed] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async () => {
    const link = url.trim()
    const cents = price.trim() ? toMinor(price, currency) : null
    const e = {
      url: mode === "paste" && !link ? t("stays.linkRequired") : undefined,
      title: title.trim() ? undefined : t("stays.nameRequired"),
      price: price.trim() && cents === null ? t("stays.priceInvalid") : undefined,
    }
    setErrors(e)
    setFailed(null)
    if (e.url || e.title || e.price) return
    setBusy(true)
    const added_via: StayIn["added_via"] = mode === "hand" ? "manual" : prefill?.via ?? "paste"
    const body: StayIn = { title: title.trim(), added_via, ...(link ? { url: link } : {}), ...(cents ? { price_per_night: { amount_minor: cents, currency } } : {}), ...(notes.trim() ? { notes: notes.trim() } : {}) }
    if (link) {
      const read = await parseLink(link)
      if (read.ok) Object.assign(body, read.data.check_in ? { check_in: read.data.check_in } : {}, read.data.check_out ? { check_out: read.data.check_out } : {}, read.data.guests ? { guests: read.data.guests } : {})
      else if (read.reason === "invalid") return fail("invalid")
    }
    // shortcut: a 402 shows the API's text; 05 6.11 wants the locked "Later" list and the `ninth_stay` paywall with "Keep in Later". Upgrade: the paywall ticket (WF-066 web paywall).
    const r = await createStay(tripId, body)
    if (!r.ok) return fail(r.reason, r.detail)
    setBusy(false)
    track("lodging_option_added", { source: added_via })
    onAdded()
  }
  const fail = (reason: string, detail?: string) => {
    setBusy(false)
    setFailed(reason === "forbidden" ? t("stays.forbidden") : (reason === "limit" || reason === "conflict") && detail ? detail : t("stays.saveFailed"))
  }

  return (
    <Modal title={t("stays.addTitle")} onClose={onClose}>
      <form className="plan__form" noValidate onSubmit={(ev) => (ev.preventDefault(), void submit())}>
        <SegmentedControl aria-label={t("stays.modes")}>
          <SegItem selected={mode === "paste"} onClick={() => setMode("paste")}>{t("stays.modePaste")}</SegItem>
          <SegItem selected={mode === "hand"} onClick={() => setMode("hand")}>{t("stays.modeHand")}</SegItem>
        </SegmentedControl>
        {prefill?.via === "bookmarklet" && <p className="h-soft" role="note">{t("stays.fromBookmarklet")}</p>}
        <TextField label={t("stays.fieldLink")} type="text" inputMode="url" autoComplete="off" spellCheck={false} value={url} error={errors.url} helper={t("stays.linkHelp")} onChange={(ev) => setUrl(ev.target.value)} />
        <TextField label={t("stays.fieldName")} value={title} error={errors.title} maxLength={300} autoComplete="off" onChange={(ev) => setTitle(ev.target.value)} />
        <TextField label={t("stays.fieldPrice")} inputMode="decimal" value={price} error={errors.price} helper={currency} autoComplete="off" onChange={(ev) => setPrice(ev.target.value)} />
        {mode === "hand" && <TextField label={t("stays.fieldNotes")} value={notes} maxLength={4000} autoComplete="off" onChange={(ev) => setNotes(ev.target.value)} />}
        {failed && (
          <p role="alert" className="h-input__error">
            <Icon name="circle-alert" size={16} />
            {failed}
          </p>
        )}
        <Btn variant="primary" type="submit" busy={busy}>{t("stays.save")}</Btn>
        <Btn variant="text" onClick={onClose}>{t("stays.close")}</Btn>
      </form>
    </Modal>
  )
}
