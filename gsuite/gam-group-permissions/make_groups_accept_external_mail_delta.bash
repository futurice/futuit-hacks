#! /bin/bash
# This script makes google groups accept mails from the outside world using GAM.
#
# Author: Markus Koskinen, Futurice Oy
# License: BSD
#
# Configuration variables:
# EXCLUSION_FILE is a file with a linebreak-separated list of emails that should not 
# accept mails from the world. Also applies to DISABLE_MODERATION, if set.
#
# DISABLE_SPAM_MODERATION if set to "true" make "spam" messages bypass the moderation queue.

PATH=${HOME}/bin:/usr/local/bin:/usr/bin:/bin:${HOME}/bin/gam
LOGFILE=${HOME}/gam-scripts/gam_groupscript_delta.log
EXCLUSION_FILE=${HOME}/gam-scripts/gam_group_exclusion.txt
DISABLE_SPAM_MODERATION=true

#
# No more configuration variables below this line, you shouldn't need to edit below
#

echo "GAM delta groups script start at $(date)" >> "$LOGFILE"

# Collect previous .all_groups for delta
touch .all_groups.tmp
cp -f .all_groups.tmp .all_groups.prev.tmp

gam print groups 2>> "$LOGFILE"|sort > .all_groups.tmp

# Overwrite old tempfile and output a delta of all groups from previous run and all groups now
echo > .processed.prev.tmp
diff --new-line-format="" --unchanged-line-format="" <(sort .all_groups.tmp) <(sort .all_groups.prev.tmp)|grep -v '^Email$'>> .processed.prev.tmp

# The csv column name 'Email' moves into the wrong place with sort
echo Email > .processed.tmp

diff --new-line-format="" --unchanged-line-format="" <(cat .processed.prev.tmp) <(sort "${EXCLUSION_FILE}"|grep -v '#')|grep -v '^Email$'>> .processed.tmp

if (( $(wc -l < .processed.tmp) > 1 )); then
  echo "Delta will be: $(grep -v '^Email$' .processed.tmp)" >> "$LOGFILE"
  gam csv .processed.tmp gam update group ~Email who_can_post_message anyone_can_post 2>> "$LOGFILE" > /dev/null
  gam csv .processed.tmp gam update group ~Email who_can_view_membership all_in_domain_can_view 2>> "$LOGFILE" > /dev/null

  if [ "${DISABLE_SPAM_MODERATION}" = "true" ]; then
    echo "Disabling moderation queues for group batch." >> "$LOGFILE"
    gam csv .processed.tmp gam update group ~Email spam_moderation_level allow 2>> "$LOGFILE" > /dev/null
  fi
else
  echo "Empty delta, no operation." >> "$LOGFILE"
fi

echo "GAM groups delta script ended at $(date)" >> "$LOGFILE"
