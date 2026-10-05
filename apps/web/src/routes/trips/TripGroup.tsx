import { useState } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router";
import { TRAVELER_COLORS } from "@hermi/tokens";
import { QueryError } from "../../components/ErrorState";
import { Skeleton } from "../../components/Skeleton";
import { Avatar, Btn, Icon, TextField, type Tone } from "../../components/kit";
import { t } from "../../lib/i18n";
import { useOnline } from "../../lib/useOnline";
import { AppShell } from "../../shell/AppShell";
import { useAuth } from "../auth/authStore";
import {
  useTrip,
  type ActionResult,
  type Person,
  type Trip,
} from "./api";
import {
  addTraveler,
  editTraveler,
  linkMe,
  setTravelers,
  unlinkMe,
  type PersonIn,
} from "./people";
import { Members } from "../invite/Members";
import { tripStrip } from "./TripStrip";
import "./trips.css";

export const tone = (color: string): Tone =>
  `t${
    Math.max(
      0,
      TRAVELER_COLORS.findIndex((c) => c.toLowerCase() === color.toLowerCase()),
    ) + 1
  }` as Tone;
const AIRPORT = /^[A-Z]{3}$/;

/** First name, color and home airports. No birthdate and no email, on purpose (05 6.21). */
function PersonForm({
  person,
  taken,
  onSave,
  onCancel,
  busy,
}: {
  person?: Person;
  taken: number;
  onSave: (b: PersonIn) => void;
  onCancel: () => void;
  busy: boolean;
}) {
  const [name, setName] = useState(person?.name ?? "");
  const [color, setColor] = useState<string>(
    person?.color ?? TRAVELER_COLORS[taken % TRAVELER_COLORS.length],
  );
  const [airports, setAirports] = useState(
    (person?.home_airports ?? []).join(", "),
  );
  const [errors, setErrors] = useState<{ name?: string; airports?: string }>(
    {},
  );
  const submit = () => {
    const codes = airports
      .split(/[\s,]+/)
      .filter(Boolean)
      .map((c) => c.toUpperCase());
    const e = {
      name: name.trim() ? undefined : t("group.nameRequired"),
      airports:
        codes.length <= 6 && codes.every((c) => AIRPORT.test(c))
          ? undefined
          : t("group.airportBad"),
    };
    setErrors(e);
    if (!e.name && !e.airports)
      onSave({ name: name.trim(), color, home_airports: codes });
  };
  return (
    <form
      className="group__form"
      aria-label={t(person ? "group.formEdit" : "group.formAdd")}
      onSubmit={(e) => (e.preventDefault(), submit())}
    >
      <TextField
        label={t("group.name")}
        value={name}
        error={errors.name}
        maxLength={60}
        autoComplete="off"
        onChange={(e) => setName(e.target.value)}
      />
      <TextField
        label={t("group.airportField")}
        helper={t("group.airportHelp")}
        value={airports}
        error={errors.airports}
        autoComplete="off"
        onChange={(e) => setAirports(e.target.value)}
      />
      <div
        role="radiogroup"
        aria-label={t("group.color")}
        className="group__colors"
      >
        {TRAVELER_COLORS.map((c, i) => (
          <label key={c} className={`group__swatch group__swatch--t${i + 1}`}>
            <input
              type="radio"
              name="color"
              aria-label={t("group.colorN", { n: i + 1 })}
              checked={color === c}
              onChange={() => setColor(c)}
            />
          </label>
        ))}
      </div>
      <div className="overview__row">
        <Btn variant="primary" type="submit" busy={busy}>
          {t("group.save")}
        </Btn>
        <Btn variant="secondary" onClick={onCancel}>
          {t("group.cancel")}
        </Btn>
      </div>
    </form>
  );
}

type RowProps = {
  p: Person;
  role?: string;
  canEdit: boolean;
  canRemove: boolean;
  online: boolean;
  onEdit: () => void;
  onRemove: () => void;
  onUnlink: () => void;
};

function Row({
  p,
  role,
  canEdit,
  canRemove,
  online,
  onEdit,
  onRemove,
  onUnlink,
}: RowProps) {
  const label = [
    p.name,
    role && t(`group.role.${role}`).toLowerCase(),
    p.home_airports.length > 0 &&
      t("group.airport", { code: p.home_airports.join(", ") }),
  ]
    .filter(Boolean)
    .join(", ");
  // shortcut: Person has no can_edit and PUT /people is owner-only, so only my own traveler gets Edit. Upgrade when the API adds it.
  return (
    <li className="h-listcard__row">
      <div role="group" aria-label={label} className="group__row">
        <Avatar tone={tone(p.color)}>{p.name.charAt(0).toUpperCase()}</Avatar>
        <span className="h-listcard__text">
          {p.name}
          {p.home_airports.length > 0 && (
            <span className="h-mono group__airport">
              {" "}
              {p.home_airports.join(", ")}
            </span>
          )}
        </span>
        {role && <span className="h-chip">{t(`group.role.${role}`)}</span>}
        {p.is_me && p.linked_user_id && (
          <Btn
            variant="text"
            mod={["sm"]}
            disabled={!online}
            onClick={onUnlink}
          >
            {t("group.unlink", { name: p.name })}
          </Btn>
        )}
        {canEdit && p.is_me && (
          <Btn
            variant="text"
            mod={["sm"]}
            disabled={!online}
            onClick={onEdit}
            aria-label={t("group.edit", { name: p.name })}
          >
            <Icon name="pencil" size={18} />
          </Btn>
        )}
        {canEdit && canRemove && (
          <Btn
            variant="text"
            mod={["sm"]}
            disabled={!online}
            onClick={onRemove}
            aria-label={t("group.remove", { name: p.name })}
          >
            <Icon name="x" size={18} />
          </Btn>
        )}
      </div>
    </li>
  );
}

function People({ trip }: { trip: Trip }) {
  const online = useOnline();
  const people = trip.travelers;
  const canEdit = trip.my_role !== "viewer";
  const [form, setForm] = useState<string | null>(null); // "add" or a person id
  const [choose, setChoose] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<"cap" | "failed" | "forbidden" | null>(null);
  // shortcut: edits need a connection (buttons disable offline); the 05 6.21 offline edit queue arrives with the offline layer.
  const run = async (f: () => Promise<ActionResult>) => {
    setBusy(true);
    const r = await f();
    setBusy(false);
    if (r.ok) {
      setMsg(null);
      setForm(null);
      setChoose(false);
    } else
      setMsg(
        r.reason === "limit"
          ? "cap"
          : r.reason === "forbidden"
            ? "forbidden"
            : "failed",
      );
  };
  const ids = people.map((p) => p.id);
  const unclaimed = !people.some((p) => p.is_me);
  const editing =
    form && form !== "add" ? people.find((p) => p.id === form) : undefined;
  return (
    <>
      {msg && (
        <p role="alert" className="h-input__error trips__note">
          <Icon name="circle-alert" size={16} />
          <span>
            {t(
              msg === "cap"
                ? "group.cap"
                : msg === "forbidden"
                  ? "group.forbidden"
                  : "group.failed",
            )}{" "}
            {msg === "cap" && <Link to="/account">{t("group.capLink")}</Link>}
          </span>
        </p>
      )}
      <section className="h-listcard" aria-labelledby="group-people">
        <h2 className="h-label h-listcard__title" id="group-people">
          {t("group.title")}
        </h2>
        {people.length === 0 ? (
          <div className="h-listcard__row group__empty">
            <strong>{t("group.emptyTitle")}</strong>
            <span className="h-soft">{t("group.emptyBody")}</span>
          </div>
        ) : (
          <ul className="edit__dests">
            {people.map((p) => (
              <Row
                key={p.id}
                p={p}
                role={p.is_me ? trip.my_role : undefined}
                canEdit={canEdit}
                canRemove={people.length > 1}
                online={online}
                onEdit={() => setForm(p.id)}
                onRemove={() =>
                  void run(() =>
                    setTravelers(
                      trip.id,
                      ids.filter((i) => i !== p.id),
                    ),
                  )
                }
                onUnlink={() => void run(() => unlinkMe(trip.id))}
              />
            ))}
          </ul>
        )}
        {unclaimed && people.length > 0 && !choose && (
          <Btn
            variant="text"
            disabled={!online}
            onClick={() => setChoose(true)}
          >
            {t("group.which")}
          </Btn>
        )}
        {choose && (
          <div
            role="group"
            aria-label={t("group.which")}
            className="group__choose"
          >
            {people
              .filter((p) => !p.linked_user_id)
              .map((p) => (
                <Btn
                  key={p.id}
                  variant="secondary"
                  mod={["sm"]}
                  disabled={busy}
                  onClick={() => void run(() => linkMe(trip.id, p.id))}
                >
                  {p.name}
                </Btn>
              ))}
          </div>
        )}
        {form && (
          <PersonForm
            key={form}
            person={editing}
            taken={people.length}
            busy={busy}
            onCancel={() => setForm(null)}
            onSave={(b) =>
              void run(() =>
                editing
                  ? editTraveler(trip.id, editing.id, b)
                  : addTraveler(trip.id, ids, b),
              )
            }
          />
        )}
        {canEdit && !form && (
          <Btn variant="text" disabled={!online} onClick={() => setForm("add")}>
            <Icon name="plus" size={18} />
            {t("group.add")}
          </Btn>
        )}
      </section>
      <Members trip={trip} />
    </>
  );
}

/** 05 6.21 Group: the People list, the members block, the link to a traveler and the traveler cap. */
export function TripGroup() {
  const { token } = useAuth();
  const { id } = useParams();
  const online = useOnline();
  const nav = useNavigate();
  const q = useTrip(id, !!token);
  if (!token) return <Navigate to="/welcome" replace />;
  return (
    <AppShell active="trips" strip={tripStrip(nav, id ?? "", "group")}>
      <div className="overview">
        {!online && (
          <p role="status" className="h-input__error trips__note">
            <Icon name="circle-alert" size={16} />
            {t("group.offline")}
          </p>
        )}
        {q.isPending && <Skeleton shape="lines" onRetry={() => void q.refetch()} />}
        {q.isError && <QueryError error={q.error} message={t("group.error")} onRetry={() => void q.refetch()} />}
        {q.data && <People trip={q.data} />}
      </div>
    </AppShell>
  );
}
