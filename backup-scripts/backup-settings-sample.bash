#!/bin/bash

# Options shared with ssh ans s3 backups
export VOLGROUP="virtualmachines" # LVM group name (check with 'lvdisplay')
export PASSFILE="backup-scripts/backup-password.pwd" # File with GPG passphrase
export SNAPSIZE="5G" # LVM snapshot size, "-L" format
export SNAPSHOT_RETENTION_COUNT=30 # Amount of snapshots to keep. 0 is infinite.

# Optional configurations
export SNAPSHOT_ROTATION_SUFFIX="dd.gz.gpg" # Only remove files with this suffix. Set "" to rotate all.

# AWS S3 specific options
export S3_BUCKET="virtualmachine-backups" # Google storage bucket name
export S3_REMOTEDIR="${VOLNAME}" # A directory within the bucket
export AWSCLI="/bin/aws"

# SSH backup specific options
# Target host and user, with public/private keys configured
export SSH_REMOTE="user@backuphost.example.com"
# A directory within the bucket
export SSH_REMOTEDIR="/mnt/backups/virtualmachines"
