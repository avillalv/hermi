import { useEffect, useMemo, useRef, useState } from "react"
import { DayChip, DayChips, Icon, LinkBtn, Btn } from "../../components/kit"
import { t } from "../../lib/i18n"
import { track } from "../../lib/track"
import type { Item } from "../itinerary/api"
import { GROUP, inOrder } from "../itinerary/meta"
import type { MapPoint } from "./cluster"
import { appleMapsUrl, googleMapsUrl } from "./handoff"
import { mountMap, type MapHandle } from "./mapView"
import "./places.css"

type NumberedDay = { day: string; n: number }

/** The stops that have a day and coordinates, numbered in each day's order (the same order as the Days view). */
function pointsOf(items: Item[], days: NumberedDay[]): (MapPoint & { dayN: number; address: string | null })[] {
  return days.flatMap((d) =>
    inOrder(items, d.day)
      .filter((i) => i.lat !== null && i.lon !== null)
      .map((i, k) => ({ id: i.id, title: i.title, n: k + 1, group: GROUP[i.category], day: d.day, dayN: d.n, address: i.address, lat: i.lat as number, lon: i.lon as number })),
  )
}

/**
 * 05 6.14 Plan map. A MapLibre map with clustered pins and a day filter; the list below is the same places and is the whole screen
 * when the map cannot load (no WebGL, offline, tiles blocked). The map is never needed to finish a task.
 */
export function PlacesMap({ items, days, online }: { items: Item[]; days: NumberedDay[]; online: boolean }) {
  const [filter, setFilter] = useState("all")
  const [selected, setSelected] = useState<string | null>(null)
  const [status, setStatus] = useState<"loading" | "ready" | "failed">("loading")
  const [attempt, setAttempt] = useState(0)
  const host = useRef<HTMLDivElement>(null)
  const handle = useRef<MapHandle | null>(null)
  const all = useMemo(() => pointsOf(items, days), [items, days])
  const shown = useMemo(() => (filter === "all" ? all : all.filter((p) => p.day === filter)), [all, filter])
  const target = shown.find((p) => p.id === selected) ?? shown[0]
  const wantMap = online && all.length > 0

  useEffect(() => void track("map_opened"), [])
  useEffect(() => {
    if (!wantMap || !host.current) return
    let dead = false
    setStatus("loading")
    mountMap(host.current, (id) => (setSelected(id), track("map_pin_selected"))).then(
      (h) => {
        if (dead) return h.destroy()
        handle.current = h
        setStatus("ready")
      },
      () => !dead && setStatus("failed"),
    )
    return () => {
      dead = true
      handle.current?.destroy()
      handle.current = null
    }
  }, [wantMap, attempt])
  useEffect(() => {
    if (status === "ready") handle.current?.update(shown)
  }, [status, shown])
  useEffect(() => handle.current?.select(selected), [selected, status])

  const handoff = (app: "apple" | "google") => track("maps_handoff", { app })
  const spot = target && { name: target.title, lat: target.lat, lon: target.lon }

  return (
    <section className="places" aria-label={t("places.mapTitle")}>
      {all.length === 0 ? (
        <p className="places__empty">{t("places.mapEmpty")}</p>
      ) : (
        <>
          <DayChips aria-label={t("places.mapFilter")}>
            <DayChip href="#all" selected={filter === "all"} onClick={(e) => (e.preventDefault(), setFilter("all"))}>{t("places.mapAll")}</DayChip>
            {days.map((d) => (
              <DayChip key={d.day} href={`#${d.day}`} selected={filter === d.day} onClick={(e) => (e.preventDefault(), setFilter(d.day))}>{`D${d.n}`}</DayChip>
            ))}
          </DayChips>
          {!online && <p role="status" className="h-input__error places__note"><Icon name="circle-alert" size={16} />{t("places.mapOffline")}</p>}
          {status === "failed" && (
            <div className="places__note">
              <p role="alert" className="h-input__error"><Icon name="circle-alert" size={16} />{t("places.mapError")}</p>
              <Btn variant="secondary" mod={["sm"]} onClick={() => setAttempt((n) => n + 1)}>{t("trips.retry")}</Btn>
            </div>
          )}
          {online && (
            <div className="places__frame" hidden={status === "failed"}>
              <div ref={host} className="places__map" />
              {status === "loading" && <div className="places__skel places__veil" role="status" aria-label={t("places.mapLoading")} />}
            </div>
          )}
          <p className="places__attr h-soft">{t("places.mapAttribution")}</p>
          {spot && (
            <div className="places__handoff">
              <LinkBtn variant="secondary" mod={["sm"]} href={appleMapsUrl(spot)} target="_blank" rel="noopener noreferrer" onClick={() => handoff("apple")}>{t("places.openApple")}</LinkBtn>
              <LinkBtn variant="secondary" mod={["sm"]} href={googleMapsUrl(spot)} target="_blank" rel="noopener noreferrer" onClick={() => handoff("google")}>{t("places.openGoogle")}</LinkBtn>
            </div>
          )}
          {shown.length === 0 ? (
            <p className="places__empty">{t("places.mapEmptyDay")}</p>
          ) : (
            <div className="h-listcard places__list" role="group" aria-label={t("places.mapList")}>
              {shown.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  className="h-listcard__row places__row"
                  aria-current={p.id === selected ? "true" : undefined}
                  onClick={() => (setSelected(p.id), handle.current?.fly(p))}
                >
                  <span className={`h-pin h-pin--num h-pin--${p.group} places__pin`} aria-hidden="true">{p.n}</span>
                  <span className="places__text">
                    <span className="h-listcard__text">{p.title}</span>
                    <span className="h-soft">{[`${t("plan.dayLabel")} ${p.dayN}`, p.address].filter(Boolean).join(", ")}</span>
                  </span>
                </button>
              ))}
            </div>
          )}
        </>
      )}
    </section>
  )
}
