# G Suite integrations

We use [Google Cloud Directory Sync](https://tools.google.com/dlpage/dirsync/) to synchronize users and groups from our internal systems to Google Suite. Unfortunately the tool is not powerful enough for our needs, so we modify the data in various ways after synchronization. Here are the automated scripts we use.

## gam-group-permissions

A quick shellscript to apply some permission bits to new G Suite groups automatically (eg. allow ouside mails, disable moderation)

## calendarsync 

Copy events from "master" calendar to user's personal calendars.

## contacts_copier

Copy contacts from Google Cloud Directory to user's contacts. This is hack mainly for iOS users, as the iOS contacts app does not read information from the Google Directory.
