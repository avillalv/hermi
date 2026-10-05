import { useEffect, useState } from "react"
import { t } from "../../lib/i18n"
import { clearConflict, startPolling, syncNow, useSyncState, FAILING_AFTER, type Conflict } from "../../lib/sync"
import { track } from "../../lib/track"
import { useOnline } from "../../lib/useOnline"
import { Btn, Icon } from "../kit"
import { Modal } from "../../routes/itinerary/Modal"
import "../../routes/itinerary/plan.css"
import "./sync-indicator.css"

type Kind = "synced" | "syncing" | "offline" | "failing"

/** "N s ago" under a minute, "N min ago" under an hour, then the clock time (05 4.21). */
function ago(lastOk: number): string {
  const s = Math.max(0, Math.floor((Date.now() - lastOk) / 1000))
  if (s < 60) return t("sync.synced", { ago: t("sync.agoSec", { n: s }) })
  if (s < 3600) return t("sync.synced", { ago: t("sync.agoMin", { n: Math.floor(s / 60) }) })
  return t("sync.syncedAt", { time: new Date(lastOk).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" }) })
}

function ConflictSheet({ tripId, conflict }: { tripId: string; conflict: Conflict }) {
  const [busy, setBusy] = useState(false)
  const pick = async (run: Conflict["keepMine"]) => {
    setBusy(true)
    try {
      await run()
    } finally {
      clearConflict(tripId)
    }
  }
  return (
    <Modal title={t("sync.conflict.title")} onClose={() => clearConflict(tripId)}>
      <p className="sync__body">{t("sync.conflict.body")}</p>
      <div className="sync__actions">
        <Btn variant="primary" busy={busy} onClick={() => void pick(conflict.keepMine)}>
          {t("sync.conflict.keepMine")}
        </Btn>
        <Btn variant="secondary" disabled={busy} onClick={() => void pick(conflict.useTheirs)}>
          {t("sync.conflict.useTheirs")}
        </Btn>
      </div>
    </Modal>
  )
}

/**
 * The sync indicator (05 4.21, 6.41): text plus icon, tap runs a sync now. The text ticks every 5 s; the polite live
 * region beside it holds the state only, so a screen reader hears state changes and never the seconds.
 * `line` sits under the destination name in the Overview hero pass, `chip` on the other sections.
 */
export function SyncIndicator({ tripId, variant = "chip" }: { tripId: string; variant?: "line" | "chip" }) {
  const s = useSyncState(tripId)
  const online = useOnline()
  const [, tick] = useState(0)
  useEffect(() => startPolling(tripId), [tripId])
  useEffect(() => {
    const h = setInterval(() => tick((n) => n + 1), 5000)
    return () => clearInterval(h)
  }, [])
  useEffect(() => {
    if (online) void syncNow(tripId) // back online: sync at once instead of waiting for the next poll
  }, [online, tripId])

  const kind: Kind = !online ? "offline" : s.failures >= FAILING_AFTER ? "failing" : s.syncing || s.lastOk === null ? "syncing" : "synced"
  const label =
    kind === "offline" ? (s.queued === 0 ? t("sync.offline") : s.queued === 1 ? t("sync.offlineOne") : t("sync.offlineMany", { n: s.queued }))
    : kind === "failing" ? t("sync.failing")
    : kind === "syncing" ? t("sync.syncing")
    : ago(s.lastOk ?? Date.now())
  const live = kind === "synced" ? t("sync.syncedLive") : label
  const warn = kind === "offline" || kind === "failing"
  return (
    <div className={`sync-wrap sync-wrap--${variant}`}>
      <button
        type="button"
        className={`sync sync--${variant}${warn ? " sync--warn" : ""}`}
        onClick={() => {
          track("sync_indicator_tapped", { state: kind })
          void syncNow(tripId, true)
        }}
      >
        {warn ? (
          <Icon name="circle-alert" size={16} className="sync__icon" />
        ) : (
          <svg className={`h-icon sync__icon${kind === "syncing" ? " sync__icon--spin" : ""}`} width={16} height={16} viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />
            <path d="M21 3v5h-5" />
            <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" />
            <path d="M8 16H3v5" />
          </svg>
        )}
        <span>{label}</span>
      </button>
      {kind === "failing" && (
        <button type="button" className="sync sync--warn sync__retry" onClick={() => void syncNow(tripId, true)}>
          {t("sync.tryNow")}
        </button>
      )}
      <span className="sync__live" aria-live="polite">
        {live}
      </span>
      {s.conflict && <ConflictSheet tripId={tripId} conflict={s.conflict} />}
    </div>
  )
}
