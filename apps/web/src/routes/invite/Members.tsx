import { useEffect, useState } from "react"
import { useNavigate, useSearchParams } from "react-router"
import { Btn, Icon } from "../../components/kit"
import { t } from "../../lib/i18n"
import { track } from "../../lib/track"
import { useOnline } from "../../lib/useOnline"
import type { Trip } from "../trips/api"
import { leaveTrip, removeMember, setRole, transferTrip, useCollaboratorMax, useInvites, useMembers, type Result } from "./collab"
import { InviteSheet } from "./InviteSheet"

/** 05 6.8 sender side and 6.21 members block: members with role chips, the collaborator count under Invite, and the Invite sheet. */
export function Members({ trip }: { trip: Trip & { editors_can_invite?: boolean } }) {
  const online = useOnline()
  const [params, setParams] = useSearchParams()
  const nav = useNavigate()
  const [open, setOpen] = useState(params.get("invite") === "1")
  const [failed, setFailed] = useState(false)
  const [done, setDone] = useState("")
  const [confirm, setConfirm] = useState(false)
  const owner = trip.my_role === "owner"
  const members = useMembers(trip.id)
  const invites = useInvites(trip.id, owner)
  const max = useCollaboratorMax(trip.id, owner)
  const meId = trip.travelers.find((p) => p.is_me)?.id
  const ownerName = members.data?.find((m) => m.role === "owner")?.display_name ?? t("group.theOwner")
  const canInvite = owner || (trip.my_role === "editor" && !!trip.editors_can_invite)
  const collaborators = (members.data?.length ?? 1) - 1
  useEffect(() => {
    if (!open) return
    track("invite_sheet_opened")
    if (params.get("invite")) setParams({}, { replace: true }) // the link only opens the sheet once
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])
  const act = async (f: () => Promise<Result>, ok = "") => {
    const r = await f()
    setFailed(!r.ok)
    setDone(r.ok ? ok : "")
    return r.ok
  }
  const leave = async () => {
    if (await act(() => leaveTrip(trip.id))) nav("/", { replace: true })
  }
  return (
    <section className="h-listcard" aria-labelledby="group-members">
      <h2 className="h-label h-listcard__title" id="group-members">
        {t("group.membersTitle")}
      </h2>
      {members.isPending && (
        <>
          <p className="h-soft" aria-live="polite">{t("group.membersLoading")}</p>
          {[0, 1].map((i) => <div key={i} className="trips__skel group__skel" aria-hidden="true" />)}
        </>
      )}
      {members.isError && (
        <div className="h-listcard__row">
          <p role="alert" className="h-input__error trips__note">
            <Icon name="circle-alert" size={16} />
            {t("group.membersError")}
          </p>
          <Btn variant="secondary" onClick={() => void members.refetch()}>{t("trips.retry")}</Btn>
        </div>
      )}
      {done && (
        <p role="status" className="trips__note">
          {done}
        </p>
      )}
      {failed && (
        <p role="alert" className="h-input__error trips__note">
          <Icon name="circle-alert" size={16} />
          {t("group.memberFailed")}
        </p>
      )}
      {members.data && (
        <ul className="edit__dests">
          {members.data.map((m) => {
            const name = m.display_name ?? t("group.theOwner")
            const you = !!m.person_id && m.person_id === meId
            return (
              <li key={m.user_id} className="h-listcard__row">
                <div role="group" aria-label={`${name}, ${t(`group.role.${m.role}`).toLowerCase()}`} className="group__row">
                  <span className="h-listcard__text">{you ? t("group.youChip") : name}</span>
                  {owner && m.role !== "owner" ? (
                    <select
                      className="h-chip"
                      aria-label={t("group.changeRole", { name })}
                      value={m.role}
                      disabled={!online}
                      onChange={(e) => void act(() => setRole(trip.id, m.user_id, e.target.value as "editor" | "viewer"), t("group.roleChanged", { name, role: t(`group.role.${e.target.value}`).toLowerCase() }))}
                    >
                      <option value="editor">{t("group.role.editor")}</option>
                      <option value="viewer">{t("group.role.viewer")}</option>
                    </select>
                  ) : (
                    <span className="h-chip">{t(`group.role.${m.role}`)}</span>
                  )}
                  {owner && m.role !== "owner" && (
                    <Btn variant="text" mod={["sm"]} disabled={!online} aria-label={t("group.removeMember", { name })} onClick={() => void act(() => removeMember(trip.id, m.user_id)).then((ok) => ok && track("member_removed"))}>
                      <Icon name="x" size={18} />
                    </Btn>
                  )}
                  {owner && m.role === "editor" && (
                    <Btn variant="text" mod={["sm"]} disabled={!online} aria-label={t("group.makeOwnerAria", { name })} onClick={() => void act(() => transferTrip(trip.id, m.user_id))}>
                      {t("group.makeOwner")}
                    </Btn>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      )}
      {canInvite ? (
        <div className="h-listcard__row group__invite">
          <Btn variant="secondary" aria-expanded={open} onClick={() => setOpen(true)}>{t("group.invite")}</Btn>
          {owner && max !== undefined && <span className="h-soft">{t("group.collabCount", { n: collaborators, max })}</span>}
        </div>
      ) : (
        <p className="h-soft h-listcard__row">{t("group.onlyOwner", { name: ownerName })}</p>
      )}
      {!owner && (
        <div className="h-listcard__row">
          {confirm ? (
            <>
              <span>{t("group.leaveConfirm")}</span>
              <Btn variant="secondary" mod={["sm"]} disabled={!online} onClick={() => void leave()}>{t("group.leaveYes")}</Btn>
              <Btn variant="text" mod={["sm"]} onClick={() => setConfirm(false)}>{t("group.cancel")}</Btn>
            </>
          ) : (
            <Btn variant="text" disabled={!online} onClick={() => setConfirm(true)}>{t("group.leave")}</Btn>
          )}
        </div>
      )}
      {open && canInvite && <InviteSheet trip={trip} owner={owner} ownerName={ownerName} pending={invites.data ?? []} onClose={() => setOpen(false)} />}
    </section>
  )
}
