#!/bin/bash
#
# Script for pushing LVM snapshots to S3
#
# Author: Markus Koskinen - License: BSD
#
# Requires: configured awscli, gpg, lvmtools etc
#

# Configuration should be stored in backup-settings.bash

# First, let's stop if anything goes wrong
# https://vaneyckt.io/posts/safer_bash_scripts_with_set_euxo_pipefail/
set -Eeuo pipefail
# Set up logger facility
source ../bash-logger/logger.bash
export LOGGER_LOGFILE="backup-s3.log"
export LOGGER_STDOUT_LEVEL=${LOG_LEVEL_WARN}
export LOGGER_STDERR_LEVEL=${LOG_LEVEL_ERROR}

trap '{ INFO "Script execution ended. Status $?"; }' EXIT

# Read settings
source backup-settings.bash

# Cursory syntax check. We expect 0 or 6 arguments.
# 0 arguments : you are colling this from another shellscript and export the needed variables
# 6 arguments : You are calling this manually or from cron, specifying the needed variables
function syntax_check {
  # Check that VOLNAME was passed as parameter
  if [ $# -eq 0 ]; then
    FATAL "VOLNAME parameter needs to be set in $1. Exiting."
    exit 100
  fi
  VOLNAME=${1}

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
  # More cleanup. Only remove files with this suffix. Set "" to rotate all.
  if [ -z "${SNAPSHOT_ROTATION_SUFFIX+x}" ]; then SNAPSHOT_ROTATION_SUFFIX="/*.dd.gz.gpg"; fi

  # REMOTEDIR - A directory within the bucket
  if [ -z "${S3_REMOTEDIR+x}" ]; then S3_REMOTEDIR="${VOLNAME}"; fi

  # Arbitrary snapshot name, used for backup filename as well
  # Just needs to be unique and descriptive
  if [ -z "${SNAPNAME+x}" ]; then SNAPNAME="snap_${VOLNAME}"; fi

  # awscli path (do not use quotes if using tilde)
  if [ -z "${AWSCLI+x}" ]; then AWSCLI=~/bin/aws; fi

  if [ -z "${LOGFILE+x}" ]; then LOGFILE="backup-logs/backup-s3-${VOLNAME}-$(date --iso-8601=date).log"; fi
}

# Clean up old snapshots, if needed
function snapshot_cleanup {
  if [ "$SNAPSHOT_RETENTION_COUNT" -eq 0 ]
  then
    WARN "SNAPSHOT_RETENTION_COUNT set to 0, not rotating snapshots"
    return
  fi

  SNAPSHOT_LIST=$($AWSCLI s3 ls "s3://${S3_BUCKET}/${S3_REMOTEDIR}/"|grep "${SNAPSHOT_ROTATION_SUFFIX}"|cut -f4 -d' '|sort|uniq|sort)
  SNAPSHOT_COUNT=$(echo -e "${SNAPSHOT_LIST}"|wc -l)

  while [ "$SNAPSHOT_COUNT" -gt "$SNAPSHOT_RETENTION_COUNT" ]
  do
    INFO "Snapshot count = $SNAPSHOT_COUNT"
    REMOVEFILE=$(log "${SNAPSHOT_LIST}"|head -n1)
    INFO "File to remove = s3://${S3_BUCKET}/${REMOTEDIR}/${REMOVEFILE}"

    if ! $AWSCLI s3 rm "s3://${S3_BUCKET}/${S3_REMOTEDIR}/${REMOVEFILE}"; then
      ERROR "Could not perform snapshot cleanup. Check your permissions."
      return
    fi

    SNAPSHOT_LIST=$($AWSCLI s3 ls "s3://${S3_BUCKET}/${S3_REMOTEDIR}/"|grep "${SNAPSHOT_ROTATION_SUFFIX}"|cut -f4 -d' '|sort|uniq|sort)
    SNAPSHOT_COUNT=$(log "${SNAPSHOT_LIST}"|wc -l)
  done
}

# A connection test with awscli, if it fails we don't continue
function awscli_check {
    if ! $AWSCLI s3 ls s3://"${S3_BUCKET}" > /dev/null; then
      ERROR "Could not access your storage bucket. Check your boto settings. Exiting."
      exit 1
    fi  
}

# Create an LVM snapshot and push it to GS, then release
function push_snapshot {
  # Create a snapshot
  /usr/sbin/lvcreate -L"${SNAPSIZE}" -s -n "${SNAPNAME}" "/dev/${VOLGROUP}/${VOLNAME}"

  # DD the image through gzip and awscli
  # With GPG, gzip forked as --fast in other process.
  # Run the pipeline in subshell so that we can pipe all output to logger
  INFO "dd started"
  (/bin/dd if="/dev/${VOLGROUP}/${SNAPNAME}" bs=16M status=none|\
    /bin/nice -n 19 /bin/pigz -9 -|\
    /bin/nice -n 19 /usr/bin/gpg -z 0 -c --batch --no-tty --passphrase-file "${PASSFILE}" |\
    ${AWSCLI} s3 cp - s3://"${S3_BUCKET}"/"${S3_REMOTEDIR}"/"${SNAPNAME}"-"$(date +%Y%m%d-%H%M.dd.gz.gpg)"
  ) 2>&1 |INFO
  INFO "dd ended"

  # Drop the snapshot
  /usr/sbin/lvremove -f "/dev/${VOLGROUP}/${SNAPNAME}"
}

# "main"
syntax_check "$@"
set_optional_defaults "$@"
awscli_check "$@"
snapshot_cleanup "$@"
push_snapshot "$@"
