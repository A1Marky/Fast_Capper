import requests
import requests
import json


########## STEP 1 #############
url = "https://cognito-idp.us-west-2.amazonaws.com/"

payload = "{\"AuthFlow\":\"USER_SRP_AUTH\",\"ClientId\":\"155mete9cpps8tp4d2faarp6po\",\"AuthParameters\":{\"USERNAME\":\"randysmith@dispostable.com\",\"SRP_A\":\"f4391615f269cf56a988397cc9a83242b81c5022a4ac009ed1d211bbbff4318f6738308cbe83cbdedcce30d12b72571487edb4d7f22fc481d35a663e44eaba5120985fd9004afa495143a38749eea60231d5f8effcb9740780e9e858d43e2e91cded2c8f6f48d89e9f2cda19ae046751804f30fa3115c6e131530114be37b9069498644e15bba1b17f07c6435deb5de4999d08afe5a0bfbf796757414b98513ad92ca78151f8dacdbc67361f09e52ae48a91000eb7307dc6864ba4b23636fc1a8213ced6a806c621956f68f79174d98383db19976add02a7cf1fa9b97c23eaf6cac78b4d67050bedd19d1592b021096719b539a05814fff1a25b52f28acf79e79833e4f1a14626f45345b54c443be5a22dd75d915f8eaafd1aab41da21c9fc2a7048b7b03f65b96a2b5837d346da6239564a3cb15f58b115ef34987c97ca3161be2ce7edff5c8feb8ab02b2aeb8a6378ec6eab38addeaa54ed396ed6a146dd9054a89b4fdbb9ffe4196cd9ff7e8546c6ee5d8e13b60d98c828906efd9c42bfca\"},\"ClientMetadata\":{}}"
headers = {
  'authority': 'cognito-idp.us-west-2.amazonaws.com',
  'accept': '*/*',
  'accept-language': 'en-US,en;q=0.9',
  'cache-control': 'no-store',
  'content-type': 'application/x-amz-json-1.1',
  'origin': 'https://the-odds-api.com',
  'referer': 'https://the-odds-api.com/',
  'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
  'sec-ch-ua-mobile': '?0',
  'sec-ch-ua-platform': '"Windows"',
  'sec-fetch-dest': 'empty',
  'sec-fetch-mode': 'cors',
  'sec-fetch-site': 'cross-site',
  'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  'x-amz-target': 'AWSCognitoIdentityProviderService.InitiateAuth',
  'x-amz-user-agent': 'aws-amplify/5.0.4 js amplify-authenticator'
}

response = requests.request("POST", url, headers=headers, data=payload)

# Parse the JSON respons
parsed_response = json.loads(response.text)

# Extract required information
challenge_name = parsed_response.get("ChallengeName", "")
challenge_parameters = parsed_response.get("ChallengeParameters", {})

# Extract nested fields
salt = challenge_parameters.get("SALT", "")
secret_block = challenge_parameters.get("SECRET_BLOCK", "")
srp_b = challenge_parameters.get("SRP_B", "")
username = challenge_parameters.get("USERNAME", "")
user_id_for_srp = challenge_parameters.get("USER_ID_FOR_SRP", "")

# Print extracted values
print("ChallengeName:", challenge_name)
print("ChallengeParameters:", challenge_parameters)
print("SALT:", salt)
print("SECRETBLOCK:", secret_block)
print("SRP_B:", srp_b)
print("USERNAME:", username)
print("USER_ID_FOR_SRP:", user_id_for_srp)




######## STEP 2 ################
import requests
import json

url = 'https://cognito-idp.us-west-2.amazonaws.com/'
headers = {
    'authority': 'cognito-idp.us-west-2.amazonaws.com',
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'no-store',
    'content-type': 'application/x-amz-json-1.1',
    'origin': 'https://the-odds-api.com',
    'referer': 'https://the-odds-api.com/',
    'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'cross-site',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'x-amz-target': 'AWSCognitoIdentityProviderService.RespondToAuthChallenge',
    'x-amz-user-agent': 'aws-amplify/5.0.4 js amplify-authenticator'
}
data = {
    "ChallengeName": "PASSWORD_VERIFIER",
    "ClientId": "155mete9cpps8tp4d2faarp6po",
    "ChallengeResponses": {
        "USERNAME": "7b234a5e-d771-4065-bd6f-258db4baff04",
        "PASSWORD_CLAIM_SECRET_BLOCK": secret_block,
        "TIMESTAMP": "Sat Jan 20 22:38:31 UTC 2024",
        "PASSWORD_CLAIM_SIGNATURE": "XYHDdOZSDJciqmhjGMShNOL7y6ipNR7kJDb9sIEAvnc="
    },
    "ClientMetadata": {}
}

response = requests.post(url, headers=headers, data=json.dumps(data))
print(response.text)

































'''# API KEY GRABBER SECTION
url = "https://accounts.the-odds-api.com/subscriptions/"

payload = "{}"
headers = {
  'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
  'sec-ch-ua-mobile': '?0',
  'Authorization': 'Bearer eyJraWQiOiJOSUYxbVdDOW9hZFB3SUlQSDFrRzY4UGdWR1BYQUNmR0w3blwvWWdPSngwdz0iLCJhbGciOiJSUzI1NiJ9.eyJzdWIiOiIxNmYyNTQ0NS01ODNiLTRiZGQtOGIyMS02OWY4NmM3ZjMwYTgiLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiaXNzIjoiaHR0cHM6XC9cL2NvZ25pdG8taWRwLnVzLXdlc3QtMi5hbWF6b25hd3MuY29tXC91cy13ZXN0LTJfR3hjd3NoaGZUIiwiY29nbml0bzp1c2VybmFtZSI6IjE2ZjI1NDQ1LTU4M2ItNGJkZC04YjIxLTY5Zjg2YzdmMzBhOCIsIm9yaWdpbl9qdGkiOiIyMDk0ZTQyZi0zODI3LTQzNTktYWE3Mi1mMGU3OGNlMjU5OWMiLCJhdWQiOiIxNTVtZXRlOWNwcHM4dHA0ZDJmYWFycDZwbyIsImV2ZW50X2lkIjoiOTlkMmU4OWMtMDFjNy00YjM5LTkwN2QtNzE4MjhhZmU4MGM5IiwidG9rZW5fdXNlIjoiaWQiLCJhdXRoX3RpbWUiOjE3MDU3ODEwNDAsIm5hbWUiOiJ4eGd0dXh2ZSIsImV4cCI6MTcwNTc4NDY0MCwiaWF0IjoxNzA1NzgxMDQwLCJqdGkiOiI1YmIwMWU2My1mOWVkLTQzMDMtYjVhMC0yNmI3NDU1YzdhMzAiLCJlbWFpbCI6Inh4Z3R1eHZlQGd1ZXJyaWxsYW1haWxibG9jay5jb20ifQ.dcrjzjlUU6sv5sPhe3K6k1qeni9-W51OINSX7zn5jCX5O8pUs-1whe0pETHCgPaOADERCC10FzArEHDFJqMmhMIsBer9RfL62DPpk7xZbqPAuP5PizBIvckvoFgHU81yGerBoANic-gIuccpbnhffBpCClMEhi4ONTJZBo8BrHFqHncfw6d9AYUQESE4lo6orlOPoaX54dkkbSiDFXPff9NB5EccZMc3Srn6AolOXjvJDIShUoiOu6fNSZI9Z6jDhccWnVeqiG5GLvc7OM1sV7JLUgOmKjxTdc5gfBstJ3q5UiPyE6QWafVVkYT7ds7X8OAq5LURS-P4ARao6IPXdA',
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  'Content-Type': 'application/json;charset=UTF-8',
  'Accept': 'application/json, text/plain, */*',
  'Referer': 'https://the-odds-api.com/',
  'sec-ch-ua-platform': '"Windows"'
}

response = requests.request("GET", url, headers=headers, data=payload)

print(response.text)

'''