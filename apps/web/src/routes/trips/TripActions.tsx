import { useId, useState } from "react";
import { Link } from "react-router";
import { Btn, Icon } from "../../components/kit";
import { t } from "../../lib/i18n";
import { useOnline } from "../../lib/useOnline";
import {
  duplicateTrip,
  patchTrip,
  restoreTrip,
  trashTrip,
  type ActionResult,
} from "./api";

export type Notice = {
  kind: "ok" | "error" | "trashed";
  text: string;
  id?: string;
};
type Target = { id: string; name: string; status: string; version?: number };

const fail = (r: Extract<ActionResult, { ok: false }>): Notice => ({
  kind: "error",
  text: t(
    r.reason === "limit"
      ? "createTrip.limit"
      : r.reason === "conflict"
        ? "editTrip.conflict"
        : "trips.actionFailed",
  ),
});

/** The one status line for trip actions: a result, a failure (alert), or "moved to trash" with Undo. */
export function NoticeBar({
  notice,
  onChange,
}: {
  notice: Notice | null;
  onChange: (n: Notice | null) => void;
}) {
  if (!notice) return null;
  const undo = async () => {
    const r = await restoreTrip(notice.id!);
    onChange(
      r.ok
        ? { kind: "ok", text: t("trips.noticeRestored", { name: r.data.name }) }
        : fail(r),
    );
  };
  return (
    <p
      role={notice.kind === "error" ? "alert" : "status"}
      className={
        notice.kind === "error" ? "h-input__error trips__note" : "trips__note"
      }
    >
      {notice.kind === "error" && <Icon name="circle-alert" size={16} />}
      {notice.text}
      {notice.kind === "trashed" && (
        <Btn variant="text" mod={["sm"]} onClick={() => void undo()}>
          {t("trips.undo")}
        </Btn>
      )}
    </p>
  );
}

/**
 * Trip actions (F-TRP-6, 05 6.5): edit for owners and editors; archive or unarchive, duplicate, move to trash. A button reveals the
 * list, the tap alternative to swipe and long press. Results go to `notify` so they survive the card moving sections.
 * The API enforces the role too; only the owner sees the rest, and a viewer sees no button.
 */
export function TripActions({
  trip,
  role,
  label,
  notify,
}: {
  trip: Target;
  role: string;
  label: string;
  notify: (n: Notice) => void;
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const panel = useId();
  const online = useOnline();
  if (role === "viewer") return null;
  const owner = role === "owner";
  const archived = trip.status === "archived";
  const run = async (go: () => Promise<Notice>) => {
    setBusy(true);
    notify(await go());
    setBusy(false);
  };
  const archive = () =>
    run(async () => {
      const r = await patchTrip(trip.id, trip.version, {
        status: archived ? "planning" : "archived",
      });
      return r.ok
        ? {
            kind: "ok",
            text: t(
              archived ? "trips.noticeUnarchived" : "trips.noticeArchived",
              { name: trip.name },
            ),
          }
        : fail(r);
    });
  const copy = () =>
    run(async () => {
      const r = await duplicateTrip(trip.id);
      return r.ok
        ? { kind: "ok", text: t("trips.noticeCopied", { name: r.data.name }) }
        : fail(r);
    });
  const trash = () =>
    run(async () => {
      const r = await trashTrip(trip.id);
      return r.ok
        ? {
            kind: "trashed",
            id: trip.id,
            text: t("trips.noticeTrashed", { name: trip.name }),
          }
        : fail(r);
    });
  const off = busy || !online;
  return (
    <div>
      <Btn
        variant="text"
        mod={["sm"]}
        aria-expanded={open}
        aria-controls={open ? panel : undefined}
        aria-label={label}
        onClick={() => setOpen(!open)}
      >
        <Icon name="ellipsis" size={20} />
      </Btn>
      {open && (
        <div id={panel} className="h-listcard actions__panel">
          <Link className="h-listcard__row" to={`/trips/${trip.id}/ai`}>
            <span className="h-listcard__text">{t("trips.ask")}</span>
          </Link>
          <Link className="h-listcard__row" to={`/trips/${trip.id}/edit`}>
            <span className="h-listcard__text">{t("trips.edit")}</span>
          </Link>
          {owner && (
            <>
              <button
                type="button"
                className="h-listcard__row"
                disabled={off}
                onClick={() => void archive()}
              >
                <span className="h-listcard__text">
                  {t(archived ? "trips.unarchive" : "trips.archive")}
                </span>
              </button>
              <button
                type="button"
                className="h-listcard__row"
                disabled={off}
                onClick={() => void copy()}
              >
                <span className="h-listcard__text">{t("trips.duplicate")}</span>
              </button>
              <button
                type="button"
                className="h-listcard__row"
                disabled={off}
                onClick={() => void trash()}
              >
                <span className="h-listcard__text">{t("trips.trash")}</span>
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
