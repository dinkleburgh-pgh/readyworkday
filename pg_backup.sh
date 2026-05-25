#!/bin/sh
# =============================================================================
# pg_backup.sh — TruckApp PostgreSQL backup script
#
# Features:
#   - Compressed custom-format dump (pg_dump -Fc)
#   - Timestamped filenames in a configurable backup directory
#   - 7-day retention (deletes backups older than RETENTION_DAYS)
#   - Logs to BACKUP_DIR/pg_backup.log and stdout
#   - Exits non-zero on failure (cron will capture it)
#
# Credentials (choose one method — do NOT hardcode here):
#   Option A — environment variables set before running this script:
#              export PGPASSWORD="your_password"
#   Option B — ~/.pgpass file (recommended for cron):
#              echo "host:port:dbname:user:password" >> ~/.pgpass
#              chmod 600 ~/.pgpass
#
# Scheduling — daily at 2:00 AM:
#   TrueNAS Scale: Dashboard → System → Tasks → Cron Jobs → Add
#     Description : TruckApp DB Backup
#     Command     : /path/to/pg_backup.sh
#     Schedule    : 0 2 * * *  (or use the "Daily at 02:00" preset)
#     Run As User : root (or the user that owns ~/.pgpass)
#     Enabled     : ✓
#
#   TrueNAS Core: Tasks → Cron Jobs → Add Cron Job (same fields)
#
#   Manual crontab (any Linux/FreeBSD host):
#     crontab -e
#     0 2 * * * /path/to/pg_backup.sh >> /var/log/pg_backup_cron.log 2>&1
# =============================================================================

set -eu

# ---------------------------------------------------------------------------
# Configuration — override via environment variables or edit defaults below.
# ---------------------------------------------------------------------------
PG_HOST="${TRUCKAPP_PG_HOST:-192.168.1.132}"
PG_PORT="${TRUCKAPP_PG_PORT:-5432}"
PG_DBNAME="${TRUCKAPP_PG_DBNAME:-coxnas}"
PG_USER="${TRUCKAPP_PG_USER:-coxnas}"
# PGPASSWORD should be set in the environment or via ~/.pgpass — never hardcode.

# Directory where backup files are written.
# Change this to your TrueNAS dataset path, e.g. /mnt/tank/truckapp-backups
BACKUP_DIR="${TRUCKAPP_BACKUP_DIR:-/mnt/tank/truckapp-backups}"

# Number of days to keep backups (older files are deleted).
RETENTION_DAYS="${TRUCKAPP_BACKUP_RETENTION_DAYS:-7}"

# Prefix for backup filenames.
BACKUP_PREFIX="truckapp"

# pg_dump binary path (override if not on PATH).
PGDUMP="${PGDUMP_BIN:-pg_dump}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"
LOG_FILE="${BACKUP_DIR}/pg_backup.log"

_log() {
    printf "[%s] %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "${LOG_FILE}"
}

_die() {
    _log "ERROR: $*"
    exit 1
}

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
if [ -z "${PG_DBNAME}" ]; then
    _die "PG_DBNAME / TRUCKAPP_PG_DBNAME is not set."
fi

if [ -z "${PG_USER}" ]; then
    _die "PG_USER / TRUCKAPP_PG_USER is not set."
fi

# Ensure backup directory exists with safe permissions.
if [ ! -d "${BACKUP_DIR}" ]; then
    mkdir -p "${BACKUP_DIR}" || _die "Cannot create backup directory: ${BACKUP_DIR}"
fi
chmod 700 "${BACKUP_DIR}"

# Verify pg_dump is available.
command -v "${PGDUMP}" > /dev/null 2>&1 || _die "pg_dump not found at '${PGDUMP}'. Install postgresql-client or set PGDUMP_BIN."

# ---------------------------------------------------------------------------
# Run backup
# ---------------------------------------------------------------------------
BACKUP_FILE="${BACKUP_DIR}/${BACKUP_PREFIX}_${TIMESTAMP}.dump"

_log "Starting backup: ${PG_HOST}:${PG_PORT}/${PG_DBNAME} → ${BACKUP_FILE}"

# Export PGPASSWORD only if set; otherwise rely on ~/.pgpass.
if [ -n "${PGPASSWORD:-}" ]; then
    export PGPASSWORD
fi

set +e
"${PGDUMP}" \
    --host="${PG_HOST}" \
    --port="${PG_PORT}" \
    --username="${PG_USER}" \
    --dbname="${PG_DBNAME}" \
    --format=custom \
    --compress=9 \
    --no-password \
    --file="${BACKUP_FILE}" 2>&1 | tee -a "${LOG_FILE}"
DUMP_EXIT=$?
set -e

# Unset PGPASSWORD from environment immediately after use.
unset PGPASSWORD 2>/dev/null || true

if [ "${DUMP_EXIT}" -ne 0 ]; then
    # Remove empty/partial dump file so it is not mistaken for a good backup.
    rm -f "${BACKUP_FILE}"
    _die "pg_dump exited with code ${DUMP_EXIT}. Backup FAILED."
fi

# Confirm the file is non-empty.
if [ ! -s "${BACKUP_FILE}" ]; then
    rm -f "${BACKUP_FILE}"
    _die "Backup file is empty after pg_dump. Backup FAILED."
fi

BACKUP_SIZE="$(du -sh "${BACKUP_FILE}" 2>/dev/null | cut -f1)"
_log "Backup successful: ${BACKUP_FILE} (${BACKUP_SIZE})"

# ---------------------------------------------------------------------------
# Retention cleanup — delete backups older than RETENTION_DAYS
# ---------------------------------------------------------------------------
_log "Pruning backups older than ${RETENTION_DAYS} days from ${BACKUP_DIR} ..."

# POSIX find: -mtime +N means strictly older than N days.
find "${BACKUP_DIR}" \
    -maxdepth 1 \
    -name "${BACKUP_PREFIX}_*.dump" \
    -mtime "+${RETENTION_DAYS}" \
    -type f | while IFS= read -r OLD_FILE; do
        _log "Deleting old backup: ${OLD_FILE}"
        rm -f "${OLD_FILE}"
    done

REMAINING="$(find "${BACKUP_DIR}" -maxdepth 1 -name "${BACKUP_PREFIX}_*.dump" -type f | wc -l | tr -d ' ')"
_log "Retention complete. ${REMAINING} backup(s) retained."

_log "Done."
exit 0
