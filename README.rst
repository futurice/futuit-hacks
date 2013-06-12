
=========================================
CES - Calendar Event Sync for Google Apps
=========================================

Introduction
============

The purpose of this script is to synchronize and manage
events from a "master calendar" (eg. futuevents@futurice.com) 
to a group of people.

The events are managed with "control tags" - for example the 
target group of people to whom an event will be synced from
the master calendar is set with a "#groups:<group1>,<group2>\n"
 - control tag.

Configuration and installation
==============================

Python 2.6 to 2.7.x is recommended. 
Requires: google-api-python-client, python-dateutil

To initialize OAuth2 tokens run: CES_googleservices.py
It should provide further instructions.


License
=======

The script is distributed under the Apache License 2.0.
It is (c) 2013 Futurice Oy. 
Portions (c) Google Inc (CES_googleservices.py)

Control tags
============

To add an event to the helsinki and tampere groups, the tag would be:

#groups: helsinki, tampere

Supported control tags
----------------------

Implemented:
#groups: <groupn>, <groupn+1>  - Add this event to members of specified groups

To be implemented:
#delete: true - Delete this event from target calendars


Control tags must start with a hash ("#") and end with a newline.
