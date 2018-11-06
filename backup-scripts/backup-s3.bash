#!/bin/bash
#
# Script for pushing LVM snapshots to S3
#
# Author: Markus Koskinen - License: BSD
#
# Requires: configured awscli, gpg, lvmtools etc
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
export LOGGER_LOGFILE="${LOGDIR}/s3-${VOLNAME}.log"
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

trap error_handler ERR INT 
trap exit_handler EXIT

# LVM does not like extra file descriptors. Don't log warnings about that
export LVM_SUPPRESS_FD_WARNINGS="y"

# Cursory syntax check. We expect 0 or 6 arguments.
# 0 arguments : you are colling this from another shellscript and export the needed variables
# 6 arguments : You are calling this manually or from cron, specifying the needed variables
function syntax_check {
  INFO "Syntax check"
  # Check that the mandatory variables exist
  arg_arr=("${S3_BUCKET}" "${S3_REMOTEDIR}" "${VOLGROUP}" "${VOLNAME}" "${PASSFILE}" "${SNAPSIZE}" "${SNAPSHOT_RETENTION_COUNT}")
  for val in "${arg_arr[@]}"
  do
    if [ -z "${val+xxx}" ]; then 
      FATAL "Variable $val was not set. Exiting."
      exit 100
    fi
    if [ -z "$val" ] && [ "${val+xxx}" = "xxx" ]; then
      FATAL "Variable $val was not set. Exiting."
      exit 100
    fi
  done
}

function set_optional_defaults {
  INFO "set optional defaults"
  # More cleanup. Only remove files with this suffix. Set "" to rotate all.
  if [ -z "${SNAPSHOT_ROTATION_SUFFIX+x}" ]; then SNAPSHOT_ROTATION_SUFFIX="/*.dd.gz.gpg"; fi

  # REMOTEDIR - A directory within the bucket
  if [ -z "${S3_REMOTEDIR+x}" ]; then S3_REMOTEDIR="${VOLNAME}"; fi

  # Arbitrary snapshot name, used for backup filename as well
  # Just needs to be unique and descriptive
  if [ -z "${SNAPNAME+x}" ]; then SNAPNAME="snap_${VOLNAME}"; fi

  # awscli path (do not use quotes if using tilde)
  if [ -z "${AWSCLI+x}" ]; then AWSCLI=~/bin/aws; fi
}

# Clean up old snapshots, if needed
function snapshot_cleanup {
  INFO "Snapshot cleanup"
  if [ "$SNAPSHOT_RETENTION_COUNT" -eq 0 ]
  then
    WARN "SNAPSHOT_RETENTION_COUNT set to 0, not rotating snapshots"
    return 0
  fi

  if [[ ! $($AWSCLI s3 ls "s3://${S3_BUCKET}/${S3_REMOTEDIR}/") ]]; then
    INFO "the directory does not exist in s3 bucket. Skipping snapshot cleanup"
    return 0
  fi

  SNAPSHOT_LIST=$($AWSCLI s3 ls "s3://${S3_BUCKET}/${S3_REMOTEDIR}/"|\
    grep "${SNAPSHOT_ROTATION_SUFFIX}"|cut -f4 -d' '|sort -u)
  SNAPSHOT_COUNT=$(echo -e "${SNAPSHOT_LIST}"|wc -l)
  INFO "Snapshot count is $SNAPSHOT_COUNT"

  while [ "$SNAPSHOT_COUNT" -gt "$SNAPSHOT_RETENTION_COUNT" ]
  do
    INFO "Snapshot count = $SNAPSHOT_COUNT"
    REMOVEFILE="$(echo "${SNAPSHOT_LIST}"|head -n1)"
    INFO "File to remove = s3://${S3_BUCKET}/${S3_REMOTEDIR}/${REMOVEFILE}"

    if ! $AWSCLI s3 rm "s3://${S3_BUCKET}/${S3_REMOTEDIR}/${REMOVEFILE}" >/dev/null 2>&1; then
      ERROR "Could not perform snapshot cleanup. Check your permissions."
      return 1
    fi

    SNAPSHOT_LIST=$($AWSCLI s3 ls "s3://${S3_BUCKET}/${S3_REMOTEDIR}/"|\
      grep "${SNAPSHOT_ROTATION_SUFFIX}"|cut -f4 -d' '|sort -u)
    SNAPSHOT_COUNT="$(echo "${SNAPSHOT_LIST}"|wc -l)"
  done
}

# A connection test with awscli, if it fails we don't continue
function awscli_check {
  INFO "aws cli check"
  if ! $AWSCLI s3 ls s3://"${S3_BUCKET}" > /dev/null; then
    ERROR "Could not access your storage bucket. Check your boto settings. Exiting."
    exit 1
  fi  
}

# Create an LVM snapshot and push it to GS, then release
function push_snapshot {
  # Create a snapshot
  INFO "Take LVM snapshot"
  if ! message="$(/usr/sbin/lvcreate -L"${SNAPSIZE}" -s -n "${SNAPNAME}" "/dev/${VOLGROUP}/${VOLNAME}" 2>&1)"
  then
    FATAL "LVM snapshot failed!"
    return 1
  fi
  INFO "LVM snapshot creted"
  INFO "lvcreate messages: ${message}"

  # DD the image through gzip and awscli
  # With GPG, gzip forked as --fast in other process.
  # Run the pipeline in subshell so that we can pipe all output to logger
  INFO "dd started"
  # Redirect the stderr of each command to file descriptor 3 and capture that as well
  exec 3>&1 #set up extra file descriptor so we can log stderr from pipeline
  if ! message="$( {
    /bin/dd if="/dev/${VOLGROUP}/${SNAPNAME}" bs=16M status=none 2>&3|\
    /bin/nice -n 19 /bin/pigz -9 - 2>&3|\
    /bin/nice -n 19 /usr/bin/gpg -z 0 -c --batch --no-tty --passphrase-file "${PASSFILE}" 2>&3|\
    ${AWSCLI} s3 cp - "s3://${S3_BUCKET}/${S3_REMOTEDIR}/${SNAPNAME}-$(date +%Y%m%d-%H%M.dd.gz.gpg)" 2>&3
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
  INFO "LVM snapshot removed"
  INFO "lvremove messages: ${message}"
}

# "main"
INFO "S3 backup for ${VOLNAME} started"
set_optional_defaults "$@"
syntax_check "$@"
awscli_check
snapshot_cleanup "$@"
push_snapshot "$@"
INFO "S3 backup for ${VOLNAME} ended"
