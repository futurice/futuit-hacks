#!/bin/bash
#
# Script for pushing LVM snapshots to an SSH host
# Author: Markus Koskinen - License: BSD
#
# Requires: configured ssh keys, gpg, lvmtools etc
#

# set pipefail so that if any command in pipe fails we get info
# https://vaneyckt.io/posts/safer_bash_scripts_with_set_euxo_pipefail/
set -u # Fail if undeclared variable is used
set -o pipefail # pipe return status will be non-zero if one of the piped commands failed
set -o posix # Posix compliance mode. Affects for example subshel return status

# Read settings
# shellcheck source=backup-settings.bash
source "$(dirname "$(realpath "${BASH_SOURCE[0]}")")/backup-settings.bash"

# Check that VOLNAME was passed as parameter
if [ $# -eq 0 ]; then
  # Not done through logger as the logger has not been initialized yet
  echo "VOLNAME parameter needs to be set in $1. Exiting." >&2
  exit 100
fi
VOLNAME=${1}

# Set up logger facility
# shellcheck source=../bash-logger/logger.bash
source "$(dirname "$(realpath "${BASH_SOURCE[0]}")")/../bash-logger/logger.bash"
export LOGGER_LOGFILE="${LOGDIR}/ssh-${VOLNAME}.log"
export LOGGER_STDOUT_LEVEL=${LOG_LEVEL_WARN}
export LOGGER_STDERR_LEVEL=${LOG_LEVEL_ERROR}

# Check the exit status of script
function exit_handler {
  exit_status=$?
  INFO "Exit handler: Script execution ended. Status: $exit_status"
  if [[ $exit_status -ne 0 ]]; then
    FATAL "Script exit status was not 0! See log file at ${LOGGER_LOGFILE}"
  fi
  exec 3>&- # release the extra file descriptor
}

# If there is error catch it and exit the script
function error_handler {
  FATAL "Uncaught error! The script is terminated"
  exit 2
}

trap error_handler ERR
trap exit_handler EXIT

# LVM does not like extra file descriptors. Don't log warnings about that
export LVM_SUPPRESS_FD_WARNINGS="y"

function set_optional_defaults {
  INFO "set optional defaults"
  # Arbitrary snapshot name, used for backup filename as well
  # Just needs to be unique and descriptive
  if [ -z "${SNAPNAME+x}" ]; then SNAPNAME="snap_${VOLNAME}"; fi
}

function snapshot_cleanup {
  INFO "Snapshot cleanup"
  if [ "$SNAPSHOT_RETENTION_COUNT" -eq 0 ]
  then
    WARN "SNAPSHOT_RETENTION_COUNT set to 0, not removing snapshots"
    return 0
  fi

  # shellcheck disable=SC2029
  if ! /usr/bin/ssh "${SSH_REMOTE}" "ls ${SSH_BASEDIR}/${VOLNAME} >/dev/null 2>&1"; then
    WARN "Can't access the directory in ssh remote. Skipping snapshot cleanup"
    return 0
  fi

  (
    # variables need to be expanded on this machine instead of remote
    # shellcheck disable=SC2029
    /usr/bin/ssh "${SSH_REMOTE}" \
      "find ${SSH_BASEDIR}/${VOLNAME}/ -name \"*.dd.gz.gpg\" -type f|sort -r|\
      tail -n +${SNAPSHOT_RETENTION_COUNT} |xargs --no-run-if-empty rm"
  )2>&1 | while read -r a; do INFO "snapshot cleanup: $a"; done

}

function push_snapshot {
   # Create a snapshot
  INFO "Take LVM snapshot"
  if ! message="$(/usr/sbin/lvcreate -L"${SNAPSIZE}" -s -n "${SNAPNAME}" "/dev/${VOLGROUP}/${VOLNAME}" 2>&1)"
  then
    FATAL "LVM snapshot failed!"
    INFO "lvcreate messages: ${message}"
    return 1
  fi
  INFO "lvcreate messages: ${message}"

  # Ensure the directory exist on remote
  # variables need to be expanded on this machine instead of remote
  # shellcheck disable=SC2029
  /usr/bin/ssh ${SSH_REMOTE} "mkdir -p ${SSH_BASEDIR}/${VOLNAME}"

  # DD the image through gzip and ssh
  # With GPG, gzip forked as --fast in other process.
  INFO "dd started"
  exec 3>&1 #set up extra file descriptor so we can log stderr from pipeline
  if ! message="$( {
    # variables need to be expanded on this machine instead of remote
    # shellcheck disable=SC2029
    /usr/bin/time /bin/dd if="/dev/${VOLGROUP}/${SNAPNAME}" bs=16M 2>&3|\
      /bin/nice -n 19 /bin/pigz -9 - 2>&3|\
      /bin/nice -n 19 /usr/bin/gpg -z 0 -c --batch --no-tty --passphrase-file "${PASSFILE}" 2>&3|\
      /usr/bin/ssh "${SSH_REMOTE}" \
        "/bin/cat > ${SSH_BASEDIR}/${VOLNAME}/${SNAPNAME}-$(date +%Y%m%d-%H%M.dd.gz.gpg)" 2>&3
  } 3>&1)"
  then
    FATAL "DD pipeline exit status was not 0!"
    INFO "dd pipeline messages: ${message}"
    return 1
  fi
    INFO "dd ended"
    INFO "dd pipeline messages: ${message}"

  # Drop the snapshot
  INFO "Remove LVM snapshot"
  if ! message="$(/usr/sbin/lvremove -f "/dev/${VOLGROUP}/${SNAPNAME}" 2>&1)"
  then
    FATAL "Removing LVM snapshot failed!"
    INFO "lvremove messages: ${message}"
    return 1
  fi
}

# main
INFO "SSH backup for ${VOLNAME} started"
set_optional_defaults
snapshot_cleanup
push_snapshot
INFO "SSH backup for ${VOLNAME} ended"