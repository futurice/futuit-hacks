A script for importing Exchange flatfiles to LDAP
=================================================

These scripts were used in a migration from Exchange
to Google Apps (Gmail). Flatfiles were exported from
Exchange (powershell scripts available near these)
and imported to LDAP. A separate sync happens from LDAP
to Google.

These scripts were made as a one-off solution and will
likely require a lot of hacking to be of use to others.

* For syntax help, please run "python LCI_main.py --help"

* Logs to INFO+ stdout and DEBUG+ LCI.log by default

* Requires python-ldap

* You should be able to enter your LDAP settings to local_LCI_settings.py

Running the import
------------------

It is recommended to run the migrations in this order:
 - aliases.txt, mailcontacts.txt, DGs.csv

* Currently three types of flatfiles are supported:

  1. alias.txt (Aliases)

  To import: python LCI_main.py --aliases data/aliases.txt

--8<-- (example input)
DisplayName        : Aarne Bertta
PrimarySmtpAddress : Aarne.Bertta@futurice.com
EmailAddresses     : {aber@futurice.com, Aarne.Bertta@futurice.eu}

--8<--

  2. mailcontacts.txt (External mails)

To import: python LCI_main.py --mailcontacts data/mailcontacts.txt

--8<-- (example input)
DisplayName          : Aarne Asiakas
PrimarySmtpAddress   : aarne.asiakas@customer.fi
ExternalEmailAddress : SMTP:aarne.asiakas@customer.fi
EmailAddresses       : aarne.asiakas@futurice.com
--8<--

  3. DGs.csv (Distribution groups)

 To import: python LCI_main.py --distributiongroups data/DGs.csv

--8<-- (example input)
"zumba-club@futurice.eu","zumba-club@futurice.com","zumba-club@futurice.fi","aarne.bertta@futurice.com","zumba-club","zumba-club@futurice.com"
"zumba-club@futurice.eu","zumba-club@futurice.com","zumba-club@futurice.fi","lorem.ipsum@futurice.com","zumba-club","zumba-club@futurice.com"
--8<--

Re-running the import (running the migrations again)
----------------------------------------------------

1. Run --aliases normally
2. Run --mailcontacts normally (new ones will be added, diff for changes in existing mailcontacts)
3. (!) Run --removedistributiongroups for the _previous_ DGs.csv
4. Run --distributiongroups for the new DGs.csv

