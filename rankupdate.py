from __future__ import print_function

import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import requests

from pprint import pprint

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# The ID and range of a spreadsheet.
SPREADSHEET_ID = '1IjRTt47oSiENPvArHEXFJZexsT7edaE1HpKERFOZjDw'     # TODO
READ_RANGE = 'A3:H99'
WRITE_RANGE_TOP_UP = 'B3'
WRITE_RANGE_TOP_DOWN = 'F3'

# Osu Authorization
API_URL = 'https://osu.ppy.sh/api/v2'
TOKEN_URL = 'https://osu.ppy.sh/oauth/token'

def getGoogleToken():
    creds = None
    # Check for token
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the future
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds


def getOsuToken():
    with open('osu_token_info.txt', 'r') as f:  # TODO
        osu_id = f.readline()
        osu_secret = f.readline()

    data = {
        'client_id': osu_id,            # TODO
        'client_secret': osu_secret,    # TODO
        'grant_type': 'client_credentials',
        'scope': 'public'
    }

    response = requests.post(TOKEN_URL, data)

    # print(response.json())

    return response.json().get('access_token')


def main():
    creds = getGoogleToken()
    osuToken = getOsuToken()
    # print(osuToken)


    try:
        # Sheets API
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()

        # osu API
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {osuToken}'
        }

        # Read Sheets
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
                                    range=READ_RANGE).execute()
        values = result.get('values', [])   # values[row][column]

        # Assign current usernames to a list with top rank distribution
        usernames = [[], []]
        for row in values:
            if row[0] != '':
                usernames[0].append(row[0])
            if row[4] != '':
                usernames[1].append(row[4])

        # print(usernames)

        if not values:
            print('No data found.')
            return

        # # Print names and ranks
        # print(values)
        # print('TOP UP')
        # for row in values:
        #     if row[0] != '':
        #         print('%s, %s' % (row[0], row[1]))
        # print('===============================')
        # print('TOP UP00')
        # for row in values:
        #     print('%s, %s' % (row[4], row[5]))

        # Make a list with better (Up) and worse (Down) ranks
        ranksUp = []
        ranksDown = []
        ranks = [ranksUp, ranksDown]
        # Grab the current list of ranks from osu API
        i = 0   # 0 - Better top, 1 - Worse top
        for topka in usernames:
            for user in topka:
                # print(user)
                params = {
                    'user': user,
                    'key': 'username',
                    'mode': 'osu'
                }

                response = requests.get(f'{API_URL}/users/{user}/osu?key=username', params=params, headers=headers)
                # print((response.json()))
                country_rank = response.json().get('statistics').get('country_rank')
                if country_rank is None:
                    country_rank = 'Inactive'
                # Update the rank
                ranks[i].append([country_rank])
            i += 1

        # Prepare data for writing information to Google Sheets
        data = [
            {
                'range': WRITE_RANGE_TOP_UP,
                'values': ranksUp
            },
            {
                'range': WRITE_RANGE_TOP_DOWN,
                'values': ranksDown
            }
        ]

        body = {
            'valueInputOption': 'USER_ENTERED',
            'data': data
        }

        # Write new ranks in valid cells
        result = service.spreadsheets().values().batchUpdate(
            spreadsheetId=SPREADSHEET_ID, body=body).execute()
        print('{0} cells updated.'.format(result.get('totalUpdatedCells')))

    except HttpError as err:
        print(err)


if __name__ == '__main__':
    main()
