import requests

url = "https://basketball-sim.appspot.com/_ah/api/nba/v1/games?date=2024-01-17&site=dk&slate=03b10f8e-aa4b-4039-b62a-9ca45efd2f72&sport=nba"

payload = {}
headers = {
  'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Microsoft Edge";v="120"',
  'Accept': 'application/json, text/plain, */*',
  'Referer': 'https://app.sabersim.com/',
  'sec-ch-ua-mobile': '?0',
  'Authorization': 'Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IjdjZjdmODcyNzA5MWU0Yzc3YWE5OTVkYjYwNzQzYjdkZDJiYjcwYjUiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3NlY3VyZXRva2VuLmdvb2dsZS5jb20vc2FiZXJzaW11aSIsImF1ZCI6InNhYmVyc2ltdWkiLCJhdXRoX3RpbWUiOjE3MDU1MTMyMjEsInVzZXJfaWQiOiJndXdOYWF5Nk90U2lWVWhndGtsTFJ1b0xOdFEyIiwic3ViIjoiZ3V3TmFheTZPdFNpVlVoZ3RrbExSdW9MTnRRMiIsImlhdCI6MTcwNTUxMzIyMSwiZXhwIjoxNzA1NTE2ODIxLCJlbWFpbCI6ImRhbm55cmVlZDI4QGRpc3Bvc3RhYmxlLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiZmlyZWJhc2UiOnsiaWRlbnRpdGllcyI6eyJlbWFpbCI6WyJkYW5ueXJlZWQyOEBkaXNwb3N0YWJsZS5jb20iXX0sInNpZ25faW5fcHJvdmlkZXIiOiJwYXNzd29yZCJ9fQ.WkPAjg8VqIYacc7JjKPXMCYpV7a-SIlF1a2GjTFiSbE4bf83z_pJap8FHkiJpSw-iQgERAhkxfhbhQwjItK1gest14nF5RiOlcmkvOXQhLynXU5j3bVEB-gIvnEL8q1xEp3izA58G-MdJRtnByRPrQ9xjJFJirOtDoXiybt57Wx2hP1Ni5TuAMfcwIWRCV-sokZ9MWYKedISGsoUdSrpBNZAk3cZPg5k4OUN8T4DNdjYZx4NPJ8cP8nMjfh-gvAZlZApYmIPk68DJ7giQAQV5-28vGVBKWqPkrkXlUYZRCAT7iNRSOzeAUl9P9KB6eiEf21Mwo59iRWwgLd2q_hKXQ',
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
  'sec-ch-ua-platform': '"Windows"'
}

response = requests.request("GET", url, headers=headers, data=payload)

print(response.text)
