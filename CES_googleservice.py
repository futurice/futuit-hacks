# -*- coding: utf-8 -*-
#
# Portions:
# Copyright (C) 2012 Google Inc.
# Copyright (C) 2013 Futurice Oy
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import gflags
import httplib2
import logging
import os
import pprint
import sys

from apiclient.discovery import build
from oauth2client.file import Storage
from oauth2client.client import AccessTokenRefreshError
from oauth2client.client import flow_from_clientsecrets
from oauth2client.tools import run

from CES_util import *

FLAGS = gflags.FLAGS

# CLIENT_SECRETS, name of a file containing the OAuth 2.0 information for this
# application, including client_id and client_secret.
# You can see the Client ID and Client secret on the API Access tab on the
# Google APIs Console <https://code.google.com/apis/console>
CLIENT_SECRETS = 'client_secrets.json'

# Helpful message to display if the CLIENT_SECRETS file is missing.
MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to download the client_secrets.json file
and save it at:

   %s

""" % os.path.join(os.path.dirname(__file__), CLIENT_SECRETS)

# Set up a Flow object to be used for authentication.
# Add one or more of the following scopes. PLEASE ONLY ADD THE SCOPES YOU
# NEED. For more information on using scopes please see
# <https://developers.google.com/+/best-practices>.
FLOW = flow_from_clientsecrets(CLIENT_SECRETS,
    scope=[
      'https://www.googleapis.com/auth/calendar',
      #'https://www.googleapis.com/auth/admin.directory.group.readonly',
      'https://www.googleapis.com/auth/directory.group.readonly',
    ],
    message=MISSING_CLIENT_SECRETS_MESSAGE)


# The gflags module makes defining command-line options easy for
# applications. Run this program with the '--help' argument to see
# all the flags that it understands.
gflags.DEFINE_enum('logging_level', 'ERROR',
    ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
    'Set the level of logging detail.')

def init_googleservices():
  # If the Credentials don't exist or are invalid, run through the native
  # client flow. The Storage object will ensure that if successful the good
  # Credentials will get written back to a file.
  logging.debug("Initializing google services.")
  storage = Storage(CES_SETTINGS['oauthStorage'])
  credentials = storage.get()

  if credentials is None or credentials.invalid:
    credentials = run(FLOW, storage)

  # Create an httplib2.Http object to handle our HTTP requests and authorize it
  # with our good Credentials.
  http = httplib2.Http()
  http = credentials.authorize(http)

  calendar_service = build('calendar', 'v3', http=http)
  admin_service = build('admin', 'directory_v1', http=http)

  try:

    logging.info("Google API services OK.")
    return (calendar_service, admin_service)

    # For more information on the Calendar API API you can visit:
    #
    #   https://developers.google.com/google-apps/calendar/firstapp
    #
    # For more information on the Calendar API API python library surface you
    # can visit:
    #
    #   https://google-api-client-libraries.appspot.com/documentation/calendar/v3/python/latest/
    #
    # For information on the Python Client Library visit:
    #
    #   https://developers.google.com/api-client-library/python/start/get_started

  except AccessTokenRefreshError:
     logging.fatal("The credentials have been revoked or expired, please re-run"
         "the application to re-authorize")
     sys.exit(1)
      


def main(argv):
  # Let the gflags module process the command-line arguments
  try:
    argv = FLAGS(argv)
  except gflags.FlagsError, e:
    print '%s\\nUsage: %s ARGS\\n%s' % (e, argv[0], FLAGS)
    sys.exit(1)

  # Set the logging according to the command-line flag
  logging.getLogger().setLevel(getattr(logging, FLAGS.logging_level))
  init_googleservices()


if __name__ == '__main__':
  main(sys.argv)
