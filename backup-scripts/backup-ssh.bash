#!/bin/bash
#
# Script for pushing LVM snapshots to an SSH host
# Author: Markus Koskinen - License: BSD
#
# Requires: configured ssh keys, gpg, lvmtools etc
#
# Remember to configure some rotating of the resulting
# backup files.


if [ $# -eq 0 ]
then
 echo "CRITICAL: VOLNAME parameter needs to be set in $1" >2
 exit 100
fi
export VOLNAME=${1}

# read settings from file
source backup-settings.bash

SNAPNAME="snap_${VOLNAME}"

function log {
  echo "$(date --iso-8601) ${1}" >> "${LOGFILE}"
}

# Create a snapshot (WARNING: currently set to 10G changes)
/usr/sbin/lvcreate -L${SNAPSIZE} -s -n "${SNAPNAME}" "/dev/${VOLGROUP}/${VOLNAME}"

# DD the image through gzip and ssh
# With GPG, gzip forked as --fast in other process.
/usr/bin/time /bin/dd if="/dev/${VOLGROUP}/${SNAPNAME}" bs=16M |\
   /bin/nice -n 19 /bin/pigz -9 -|\
   /bin/nice -n 19 /usr/bin/gpg -z 0 -c --batch --no-tty --passphrase-file "${PASSFILE}" |\
   /usr/bin/ssh -p ${SSH_PORT} "${REMOTE}" \
      "/bin/cat > ${REMOTEDIR}/${SNAPNAME}-$(date +%Y%m%d-%H%M.dd.gz.gpg)"

# Drop the snapshot
/usr/sbin/lvremove -f "/dev/${VOLGROUP}/${SNAPNAME}"
