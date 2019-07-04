#!/bin/env python

'''
Add Github users to okta.

Usage:
export OKTA_BASEURL=https://your_domain.okta.com
export OKTA_TOKEN=asdgfdsg
export OKTA_GROUPNAME=app-GitHub
python main.py
'''
import sys
import os
import csv
import json
import requests

def get_okta_user(username):
    params = {
        'q': username,
        'limit': '1'
    }

    response = requests.get(f'{OKTA_BASEURL}/api/v1/users', params=params, headers=OKTA_HEADERS)
    response.raise_for_status()
    # okta returns list of users. return just the first
    return response.json()[0]

def set_github_username(userid, gh_username):
    payload = {
        'profile': {
            'github_username': gh_username
        }
    }

    response = requests.post(f'{OKTA_BASEURL}/api/v1/users/{userid}', data=json.dumps(payload), headers=OKTA_HEADERS)
    response.raise_for_status()
    
def get_okta_group(groupname):
    params = {
        'q': groupname,
        'limit': '1'
    }

    response = requests.get(f'{OKTA_BASEURL}/api/v1/groups', params=params, headers=OKTA_HEADERS)
    response.raise_for_status()
    # okta returns list of groups. return just the first
    return response.json()[0]

def add_user_to_group(groupid, userid):
    response = requests.put(f'{OKTA_BASEURL}/api/v1/groups/{groupid}/users/{userid}',  headers=OKTA_HEADERS)
    response.raise_for_status()

### MAIN ###

OKTA_BASEURL = os.environ['OKTA_BASEURL']
OKTA_TOKEN = os.environ['OKTA_TOKEN']
OKTA_HEADERS = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': f'SSWS {OKTA_TOKEN}'
    }
OKTA_GROUPNAME = os.environ['OKTA_GROUPNAME']

csv_filename = sys.argv[1]
print(f'Using file {csv_filename}')

group = get_okta_group(OKTA_GROUPNAME)
groupname = group['profile']['name']
groupid = group['id']
print(f'Found group "{groupname}" with id {groupid}')


with open(csv_filename, newline='') as csvfile:
    csvreader = csv.reader(csvfile, delimiter=',')
    for row in csvreader:
        username = row[0]
        github_username = row[1]
        print(f'Get user: {username}')
        user = get_okta_user(username)
        userid = user['id']
        print(f'Set userID {userid} GitHub username to {github_username}')
        set_github_username(userid, github_username)
        print(f'add UserID {userid} to group {groupid}')
        add_user_to_group(groupid,userid)
