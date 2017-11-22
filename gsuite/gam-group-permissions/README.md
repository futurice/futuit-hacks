# Google apps group permissions

### A quick shellscript to apply some permission bits to new G Suite groups automatically

By default google groups (also used as mailing lists) are created with permissions that only 
allow organization-users to successfully send mails through them.

This is not how everyone always wants to use these lists, but to have them open to the world instead.
To mitigate this issue you can run this script in cron to apply the more relaxed permissions.
Furthermore, allow everyone in the organization to see group members.

Additionally you can set the script to disable spam moderation and have an exclusion list 
for which groups the settings will not be applied.

It uses a tool called "GAM" ( https://github.com/jay0lee/GAM )
