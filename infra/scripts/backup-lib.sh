# Shared helpers for backup-dump.sh and restore-drill.sh (WF-039). Sourced, not run.
# Never print a secret. Passwords go to libpq through PGPASSWORD, R2 credentials to curl on stdin.

die() { echo "error: $*" >&2; exit 1; }

# Put the PostgreSQL 18 client tools on PATH: PG_BIN first, then the usual install folders.
find_pg() {
  local d
  for d in "${PG_BIN:-}" "/c/Program Files/PostgreSQL/18/bin" /usr/lib/postgresql/18/bin /usr/pgsql-18/bin /opt/homebrew/opt/postgresql@18/bin; do
    [ -n "$d" ] && [ -x "$d/pg_dump" -o -x "$d/pg_dump.exe" ] && { PATH="$d:$PATH"; break; }
  done
  command -v pg_dump >/dev/null && command -v pg_restore >/dev/null && command -v psql >/dev/null \
    || die "PostgreSQL client tools (pg_dump, pg_restore, psql) not found. Install PostgreSQL 18 or set PG_BIN."
}

need_openssl() { command -v openssl >/dev/null || die "openssl not found"; }

need_key() { [ -n "${BACKUP_ENCRYPTION_KEY:-}" ] || die "BACKUP_ENCRYPTION_KEY is not set (the key is held outside Render)"; }

# Same cipher both ways. The key reaches openssl through the environment, never argv.
encrypt() { openssl enc -aes-256-cbc -pbkdf2 -iter 600000 -salt -pass env:BACKUP_ENCRYPTION_KEY; }
decrypt() { openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -pass env:BACKUP_ENCRYPTION_KEY; }

# apply_url URL: export PGHOST, PGPORT, PGUSER, PGPASSWORD from a postgresql:// URL (a +driver suffix
# is ignored) and set URL_DB to its database name. An empty URL leaves the PG* environment alone.
apply_url() {
  [ -n "$1" ] || return 0
  local re='^postgres(ql)?(\+[a-z0-9]+)?://([^:@/]*)(:([^@]*))?@([^:/?]+)(:([0-9]+))?(/([^?]*))?' pw
  [[ "$1" =~ $re ]] || die "connection string is not a postgresql:// URL"
  export PGUSER="${BASH_REMATCH[3]}" PGHOST="${BASH_REMATCH[6]}"
  [ -n "${BASH_REMATCH[8]}" ] && export PGPORT="${BASH_REMATCH[8]}"
  pw="${BASH_REMATCH[5]}"
  # decode only %XX, so a backslash or a stray % in the password is left alone
  local out="" hex re2='^([^%]*)%([0-9A-Fa-f]{2})(.*)$'
  while [[ "$pw" =~ $re2 ]]; do
    printf -v hex '\x%s' "${BASH_REMATCH[2]}"; printf -v hex '%b' "$hex"
    out+="${BASH_REMATCH[1]}$hex"; pw="${BASH_REMATCH[3]}"
  done
  out+="$pw"
  [ -z "$out" ] || export PGPASSWORD="$out"
  URL_DB="${BASH_REMATCH[10]}"
  return 0
}

# r2 METHOD KEY [extra curl args]: signed S3 call to the backups bucket. Credentials go to curl on stdin.
r2() {
  local method="$1" key="$2"; shift 2
  [ -n "${R2_ENDPOINT_URL:-}" ] && [ -n "${R2_ACCESS_KEY_ID:-}" ] && [ -n "${R2_SECRET_ACCESS_KEY:-}" ] && [ -n "${R2_BUCKET_BACKUPS:-}" ] \
    || die "R2_ENDPOINT_URL, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY and R2_BUCKET_BACKUPS must be set"
  command -v curl >/dev/null || die "curl not found"
  printf 'user = "%s:%s"\n' "$R2_ACCESS_KEY_ID" "$R2_SECRET_ACCESS_KEY" |
    curl -sS --fail -K - -X "$method" --aws-sigv4 "aws:amz:auto:s3" \
      -H "x-amz-content-sha256: UNSIGNED-PAYLOAD" "$@" "${R2_ENDPOINT_URL%/}/$R2_BUCKET_BACKUPS/$key"
}
