#!/bin/sh
set -eu

if [ "${CONFIRM_RESTORE:-}" != "RESTORE" ]; then
  echo "Set CONFIRM_RESTORE=RESTORE to acknowledge that the target database will be replaced." >&2
  exit 2
fi

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "Usage: restore.sh /backups/portfolio-YYYYMMDDTHHMMSSZ.dump [/backups/portfolio-media-YYYYMMDDTHHMMSSZ.tar.gz]" >&2
  exit 2
fi

case "$1" in
  /backups/portfolio-*.dump) backup="$1" ;;
  *) echo "Restore input must be a portfolio dump inside /backups." >&2; exit 2 ;;
esac

test -f "${backup}"
test -f "${backup}.sha256"
(cd /backups && sha256sum -c "$(basename "${backup}.sha256")")

pg_restore --clean --if-exists --no-owner --no-acl --single-transaction --dbname="${PGDATABASE}" "${backup}"
printf 'database_restore_completed=%s\n' "${backup}"

if [ "$#" -eq 2 ]; then
  case "$2" in
    /backups/portfolio-media-*.tar.gz) media_backup="$2" ;;
    *) echo "Media restore input must be a portfolio media archive inside /backups." >&2; exit 2 ;;
  esac
  test -f "${media_backup}"
  test -f "${media_backup}.sha256"
  (cd /backups && sha256sum -c "$(basename "${media_backup}.sha256")")
  if tar -tzf "${media_backup}" | grep -E '(^/|(^|/)\.\.(/|$))' >/dev/null; then
    echo "Media archive contains an unsafe path." >&2
    exit 3
  fi
  find /media -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
  tar -xzf "${media_backup}" -C /media
  chown -R "${MEDIA_UID:-10001}:${MEDIA_GID:-10001}" /media
  chmod 0750 /media
  printf 'media_restore_completed=%s\n' "${media_backup}"
fi
