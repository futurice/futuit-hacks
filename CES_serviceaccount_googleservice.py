# -*- coding: utf-8 -*-
#
# Portions:
# Copyright (C) 2012 Google Inc.
# Copyright (C) 2013 Futurice Oy

import httplib2
import sys

from apiclient.discovery import build
from oauth2client.client import SignedJwtAssertionCredentials

from CES_util import *
from local_settings import *

"""Email of the Service Account"""
SERVICE_ACCOUNT_EMAIL = CES_PRIVATE_SETTINGS['SERVICE_ACCOUNT_EMAIL']

"""Path to the Service Account's Private Key file"""
SERVICE_ACCOUNT_PKCS12_FILE_PATH = CES_PRIVATE_SETTINGS['SERVICE_ACCOUNT_PKCS12_FILE_PATH']

def createDirectoryService(user_email=CES_PRIVATE_SETTINGS['ADMIN_ACCOUNT_EMAIL']):
    """ Return a directory service object, as authenticated user user_email. """
    return createService(scope="https://www.googleapis.com/auth/directory.group.readonly",
         build_type="admin",
         build_version="directory_v1",
         user_email=user_email)

def createCalendarService(user_email=CES_PRIVATE_SETTINGS['ADMIN_ACCOUNT_EMAIL']):
    """ Return a calendar service object, as authenticated user user_email. """
    return createService(scope="https://www.googleapis.com/auth/calendar",
         build_type="calendar",
         build_version="v3",
         user_email=user_email)

def createService(scope, build_type, build_version, user_email):
  """Build and returns a Drive service object authorized with the service accounts
  that act on behalf of the given user.

  Args:
    user_email: The email of the user.
  Returns:
    Calendar service object.
  """
  try:
      f = file(SERVICE_ACCOUNT_PKCS12_FILE_PATH, 'rb')
      key = f.read()
      f.close()
  except IOError:
      logging.fatal("Failed to open PKCS12 keyfile.")
      sys.exit(1)
  except:
      logging.fatal("Unspecified error opening PKCS12 keyfile.")
      sys.exit(1)
      

  credentials = SignedJwtAssertionCredentials(SERVICE_ACCOUNT_EMAIL, key,
      scope=scope, prn=user_email)

  http = httplib2.Http()
  http = credentials.authorize(http)

  return build(build_type, build_version, http=http)
