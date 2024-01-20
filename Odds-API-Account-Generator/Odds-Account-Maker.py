import requests
import json
import time
import re
import csv
from guerrillamail import GuerrillaMailSession

# Constants
BASE_URL = "https://cognito-idp.us-west-2.amazonaws.com/"
CLIENT_ID = '155mete9cpps8tp4d2faarp6po'
COMMON_HEADERS = {
    'authority': 'cognito-idp.us-west-2.amazonaws.com',
    'accept': '*/*',
    'cache-control': 'max-age=0',
    'content-type': 'application/x-amz-json-1.1',
    'origin': 'https://the-odds-api.com',
    'referer': 'https://the-odds-api.com/',
}

def make_api_request(url, headers, payload):
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as err:
        print(f"Request error: {err}")
        return None

def create_account(username: str, password: str):
    payload = {
        "ClientId": CLIENT_ID,
        "Username": username,
        "Password": password,
        "UserAttributes": [
            {"Name": "name", "Value": username.split('@')[0]},
            {"Name": "email", "Value": username}
        ],
        "ValidationData": None
    }
    headers = COMMON_HEADERS.copy()
    headers.update({'x-amz-target': 'AWSCognitoIdentityProviderService.SignUp'})
    print(CLIENT_ID)
    return make_api_request(BASE_URL, headers, payload)

def confirm_signup(username: str, verification_code: str):
    payload = {
        "ClientId": CLIENT_ID,
        "ConfirmationCode": verification_code,
        "Username": username,
        "ForceAliasCreation": True
    }
    headers = COMMON_HEADERS.copy()
    headers.update({'x-amz-target': 'AWSCognitoIdentityProviderService.ConfirmSignUp'})
    return make_api_request(BASE_URL, headers, payload)

# Main script for account creation and verification
data = []
for _ in range(1): # <------------------------ CHANGE THIS LINE TO HOW MANY ACCOUNTS YOU WANT CREATED AND VERIFIED
    session = GuerrillaMailSession()
    email = session.get_session_state()['email_address']
    initial_email_ids = {email.guid for email in session.get_email_list()}
    
    response = create_account(email, password="Password#123")
    if response is not None:
        user_sub = response.get('UserSub')
        print(f'UserSub: {user_sub}')

    time.sleep(3)

    while True:
        email_list = session.get_email_list()
        new_emails = [email for email in email_list if email.guid not in initial_email_ids]

        if new_emails:
            first_new_email = session.get_email(new_emails[0].guid)
            match = re.search(r'Your verification code is (\d+)', first_new_email.body)
            if match:
                verification_code = match.group(1)
                confirm_response = confirm_signup(email, verification_code)
                if confirm_response is not None:
                    data.append((email, verification_code))
                break
            else:
                print("Couldn't find a verification code in the email body.")
                break
        else:
            print("No new emails in the inbox, retrying in 3 seconds...")
            time.sleep(3)

with open('Odds-API-Account-Generator/odds-api-created-accounts.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Email", "Verification Code"])
    writer.writerows(data)
