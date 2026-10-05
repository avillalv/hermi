#!/usr/bin/env bash
# WF-039: weekly encrypted logical dump. pg_dump (custom format) | openssl AES-256 | R2 backups bucket.
# Run weekly (Sunday 03:00 UTC, 02-architecture.md section 6). The R2_* values must be the credentials of
# the second Cloudflare account, so a compromise of the first one cannot reach the dumps.
#
#   DUMP_DATABASE_URL        postgresql:// URL of the database to dump (or the PG* variables)
#   BACKUP_ENCRYPTION_KEY    passphrase, held outside Render (password manager)
#   R2_ENDPOINT_URL, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_BACKUPS
#
# Usage: backup-dump.sh [--out FILE] [--no-upload]
# --out writes the encrypted dump to FILE (a path in the current directory is safest on Windows).
# The plaintext dump never touches the disk. Prints the object key or file written, never a secret.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$here/backup-lib.sh"

out="" upload=1
while [ $# -gt 0 ]; do
  case "$1" in
    --out) out="${2:?--out needs a file}"; shift 2 ;;
    --no-upload) upload=0; shift ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done
[ -n "$out" ] || [ "$upload" = 1 ] || die "--no-upload needs --out"

need_key; need_openssl; find_pg
URL_DB=""; apply_url "${DUMP_DATABASE_URL:-}"; export PGUSER="${PGUSER:-postgres}" PGCONNECT_TIMEOUT=15
db="${URL_DB:-${PGDATABASE:-hermi}}"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
key="hermi-db/hermi-$stamp.dump.enc"

tmp="${out:-$(mktemp)}"
trap '[ -n "$out" ] || rm -f "$tmp"' EXIT
pg_dump -w -Fc "$db" | encrypt > "$tmp"
[ -s "$tmp" ] || die "dump is empty"

if [ -n "$out" ]; then echo "wrote $out"; fi
if [ "$upload" = 1 ]; then
  r2 PUT "$key" --upload-file "$tmp" >/dev/null
  echo "uploaded $key"
fi
