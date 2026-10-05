#!/usr/bin/env bash
# WF-039: restore drill. Decrypt a dump, restore it into a scratch database, smoke test it, time it
# against the 1 hour RTO (10-quality-security-launch.md), then drop the scratch database.
#
# Usage:
#   restore-drill.sh                 latest dump from the R2 backups bucket
#   restore-drill.sh --file F        a local encrypted dump (made by backup-dump.sh)
#   restore-drill.sh --local         self-test: dump the local database, encrypt, restore, smoke test; no R2
# Options: --scratch-db NAME (must start with hermi_ and must not exist), --keep (do not drop it)
#
# Env: BACKUP_ENCRYPTION_KEY (not needed with --local), RESTORE_ADMIN_URL (postgresql:// URL of the server
# that may create databases; or the PG* variables), DUMP_DATABASE_URL (--local source), R2_* (see backup-dump.sh),
# RTO_SECONDS (default 3600), PG_BIN. Only hermi_* databases are ever created or dropped. Exit 0 = PASS.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$here/backup-lib.sh"

file="" local_mode=0 keep=0 scratch="hermi_drill_$(date -u +%Y%m%d%H%M%S)"
while [ $# -gt 0 ]; do
  case "$1" in
    --file) file="${2:?--file needs a path}"; shift 2 ;;
    --local|--self-test) local_mode=1; shift ;;
    --scratch-db) scratch="${2:?--scratch-db needs a name}"; shift 2 ;;
    --keep) keep=1; shift ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

# Guards first, before any tool runs.
[[ "$scratch" =~ ^hermi_[a-z0-9_]+$ ]] || die "scratch database name must start with hermi_ (letters, digits, underscores): refusing '$scratch'"
if [ "$local_mode" = 1 ] && [ -z "${BACKUP_ENCRYPTION_KEY:-}" ]; then
  need_openssl; BACKUP_ENCRYPTION_KEY="$(openssl rand -hex 32)"; export BACKUP_ENCRYPTION_KEY  # self-test only
fi
need_key; need_openssl; find_pg
rto="${RTO_SECONDS:-3600}"

SECONDS=0
tmp="$(mktemp)"; created=0; ADMIN_DB=postgres
admin_env() { URL_DB=""; apply_url "${RESTORE_ADMIN_URL:-}"; [ -n "${PGUSER:-}" ] || export PGUSER=postgres; export PGCONNECT_TIMEOUT=15; ADMIN_DB="${URL_DB:-postgres}"; }
cleanup() {
  rm -f "$tmp"
  if [ "$created" = 1 ] && [ "$keep" = 0 ]; then
    psql -wqAt -d "$ADMIN_DB" -c "DROP DATABASE IF EXISTS $scratch WITH (FORCE)" >/dev/null 2>&1 || echo "warning: could not drop $scratch" >&2
  fi
}
trap cleanup EXIT

src_db=""
# Source counts use the DUMP_DATABASE_URL server and credentials, in a subshell so PG* stays untouched.
src_q() { ( URL_DB=""; apply_url "${DUMP_DATABASE_URL:-}"; export PGUSER="${PGUSER:-postgres}"; psql -wqAt -d "$src_db" -c "$1" ); }
if [ "$local_mode" = 1 ]; then
  [ -z "$file" ] || die "--local and --file cannot be combined"
  echo "[1/4] self-test: dumping the local database"
  bash "$here/backup-dump.sh" --no-upload --out "$tmp" >/dev/null || die "local dump failed"
  src_db="$(URL_DB=""; apply_url "${DUMP_DATABASE_URL:-}"; echo "${URL_DB:-${PGDATABASE:-hermi}}")"
  file="$tmp"
elif [ -z "$file" ]; then
  echo "[1/4] downloading the latest dump from R2"
  latest="$(r2 GET "?list-type=2&prefix=hermi-db/" | grep -o '<Key>[^<]*</Key>' | sed 's/<[^>]*>//g' | sort | tail -1)"
  [ -n "$latest" ] || die "no dumps found in the backups bucket"
  r2 GET "$latest" -o "$tmp"
  echo "      $latest"
  file="$tmp"
else
  [ -f "$file" ] || die "file not found: $file"
  echo "[1/4] using $file"
fi

echo "[2/4] restoring into $scratch"
admin_env
[ "$(psql -wqAt -d "$ADMIN_DB" -c "SELECT count(*) FROM pg_database WHERE datname = '$scratch'")" = 0 ] \
  || die "database $scratch already exists, refusing to touch it"
psql -wqAt -d "$ADMIN_DB" -c "CREATE DATABASE $scratch" >/dev/null; created=1
for r in hermi_owner hermi_definer hermi_app; do
  [ "$(psql -wqAt -d "$ADMIN_DB" -c "SELECT count(*) FROM pg_roles WHERE rolname = '$r'")" = 1 ]     || die "role $r is missing on this server: run infra/db/bootstrap.sql first (dumps keep owners and grants)"
done
decrypt < "$file" | pg_restore -w -d "$scratch" || die "restore failed (wrong key, corrupt dump or a role is missing: run infra/db/bootstrap.sql on this server first)"

echo "[3/4] smoke test"
fail=0
q() { psql -wqAt -d "$scratch" -c "$1"; }
bad() { echo "  FAIL $*"; fail=1; }
for t in users trips trip_members deletion_requests; do
  if [ "$(q "SELECT to_regclass('public.$t') IS NOT NULL")" = t ]; then
    n="$(q "SELECT count(*) FROM $t")"; echo "  ok   $t: $n rows"
    if [ -n "$src_db" ]; then
      want="$(src_q "SELECT count(*) FROM $t")"
      [ "$n" = "$want" ] || bad "$t has $n rows, source has $want"
    fi
  else bad "table $t is missing"; fi
done
versions="$here/../../apps/api/hermi/migrations/versions"
ver="$(q "SELECT version_num FROM alembic_version" 2>/dev/null || true)"
head="$(sed -n 's/^revision = "\(.*\)"/\1/p' "$(ls "$versions"/[0-9]*.py | sort | tail -1)")"
if [ -z "$ver" ]; then bad "alembic_version is empty"
elif grep -q "^revision = \"$ver\"" "$versions"/[0-9]*.py; then
  if [ "$ver" = "$head" ]; then echo "  ok   alembic head $ver"; else echo "  warn dump is at $ver, repo head is $head (fine if a release landed since the dump)"; fi
else bad "alembic version $ver is not a known revision"; fi
# Deleted users stay deleted: no completed deletion request may still have a user row.
zombies="$(q "SELECT count(*) FROM deletion_requests d JOIN users u ON u.id = d.user_id WHERE d.status = 'completed'")"
if [ "$zombies" = 0 ]; then echo "  ok   deleted users stay deleted"; else bad "$zombies completed deletions still have a user row (re-run the purge, see the runbook)"; fi

# Owners, grants and row level security survive the restore (the dump keeps them).
n="$(q "SELECT count(*) FROM pg_proc WHERE prosecdef AND pronamespace = 'public'::regnamespace AND proowner <> 'hermi_definer'::regrole")"
if [ "$n" = 0 ]; then echo "  ok   definer functions owned by hermi_definer"; else bad "$n security definer functions are not owned by hermi_definer"; fi
# The three RLS helpers (03 6.2) are public per 03 and the policies call them as hermi_app; trips_add_owner_member is a trigger function and cannot be called directly. Every other definer must not be public.
n="$(q "SELECT count(*) FROM pg_proc WHERE prosecdef AND pronamespace = 'public'::regnamespace AND proname NOT IN ('can_edit_trip','is_trip_owner','trips_add_owner_member','visible_trip_ids') AND has_function_privilege('public', oid, 'EXECUTE')")"
if [ "$n" = 0 ]; then echo "  ok   no privileged definer function executable by public"; else bad "$n security definer functions are executable by public"; fi
if [ "$(q "SELECT has_table_privilege('hermi_app', 'trips', 'SELECT')")" = t ]; then echo "  ok   hermi_app can read trips"; else bad "hermi_app lost SELECT on trips"; fi
n="$(q "SELECT count(*) FROM pg_class WHERE relname IN ('trips','trip_members','itinerary_items','lodging_votes','saved_place_votes','notes','runs') AND relnamespace = 'public'::regnamespace AND NOT relforcerowsecurity")"
if [ "$n" = 0 ]; then echo "  ok   row level security still forced on tenant tables"; else bad "$n tenant tables lost FORCE ROW LEVEL SECURITY"; fi

elapsed=$SECONDS
echo "[4/4] elapsed ${elapsed}s, RTO ${rto}s"
[ "$elapsed" -le "$rto" ] || bad "restore took longer than the RTO"
if [ "$fail" = 0 ]; then echo "PASS"; exit 0; fi
echo "FAIL"; exit 1
