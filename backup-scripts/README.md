# Some scripts for handling LVM snapshot backups

These scripts are originally from https://github.com/mkoskinen/backup-scripts
They have been modified since then

The idea of these scripts is to take LVM snapshots of LVM partitions,
compress, encrypt and push them to AWS S3 storage or a remote SSH server.
You can launch these through cron.

*These are shell scripts so things can easily go wrong, please
be careful.*
https://github.com/futurice/futuit-hacks/backup-scripts

Requires lvmtools, gpg, gzip, awscli

Feel free to change as you wish.

## ./backup-s3.bash

Backup LVM volume to AWS S3 bucket. The backup file is gpg encrypted and
gzipped.

## ./backup-ssh.bash

Backup LVM volume to ssh host. The backup file is gpg encrypted and
gzipped.

You need to set up ssh key authentication for this to work.

Depending on the filesystem layout on the backup server, you might consider
using LVM partitions, quotas, or sticky bits to take care of file permissions
and to have safeguards against filling the system by accident.

## Extracting / Recovering

"mengpo"  is just example LVM volume name

From file:

```
% gpg -d --batch --passphrase-file mengpo.pwd snap_mengpo-20151022-0800.dd.gz.gpg|gunzip -> targetfile_or_device.dd
```
