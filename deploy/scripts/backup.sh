#!/bin/sh
set -eu

umask 077
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
target="/backups/portfolio-${timestamp}.dump"
media_target="/backups/portfolio-media-${timestamp}.tar.gz"

pg_dump --format=custom --compress=9 --no-owner --no-acl --file="${target}"
sha256sum "${target}" > "${target}.sha256"
if find /media -type l -print -quit | grep -q .; then
  echo "Media backup refused because symbolic links are not supported." >&2
  exit 3
fi
tar -czf "${media_target}" -C /media .
sha256sum "${media_target}" > "${media_target}.sha256"
find /backups -type f -name 'portfolio-*.dump*' -mtime "+${BACKUP_RETENTION_DAYS:-14}" -delete
find /backups -type f -name 'portfolio-media-*.tar.gz*' -mtime "+${BACKUP_RETENTION_DAYS:-14}" -delete
printf 'database_backup_created=%s\nmedia_backup_created=%s\n' "${target}" "${media_target}"
