import requests
import json
import os
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
import datetime
from decimal import Decimal


# Load environment variables
load_dotenv()

SABERSIM_API_KEY = os.getenv('SABERSIM_API_KEY')

def get_auth_token(email: str, password: str) -> str:
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={SABERSIM_API_KEY}"
    
    payload = json.dumps({
        "returnSecureToken": True,
        "email": email,
        "password": password
    })
    
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    }
    
    response = requests.post(url, headers=headers, data=payload)
    response_data = response.json()
    
    if response.status_code == 200:
        return response_data.get("idToken")
    raise Exception("Failed to get auth token: " + response_data.get("error", {}).get("message", ""))

def get_slates(auth_token: str, date: str, sport: str = 'nba') -> list:
    url = f"https://basketball-sim.appspot.com/_ah/api/nba/v1/slates?date={date}&sport={sport}"
    
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {auth_token}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    }
    
    response = requests.get(url, headers=headers)
    response_data = response.json()
    
    if response.status_code == 200 and isinstance(response_data, dict) and 'slates' in response_data:
        slates_list = [slate.get('id') for slate in response_data.get('slates', []) if slate.get('site').lower() == 'fd']
        #print("Slate IDs:", slates_list)
        return slates_list
    
    raise Exception("Failed to get slates: HTTP " + str(response.status_code))


def get_player_projections(auth_token: str, date: str, slate_ids: list, sport: str = 'nba', site: str = 'fd') -> pd.DataFrame:
    url = "https://basketball-sim.appspot.com/endpoints/get_player_projections"
    headers = {
        'Authorization': f'Bearer {auth_token}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/plain, */*',
    }

    all_players_data = []
    for slate_id in slate_ids:
        payload = json.dumps({
            "conditionals": [],
            "date": date,
            "percentile": "0",
            "site": site,
            "slate": slate_id,
            "sport": sport
        })

        response = requests.post(url, headers=headers, data=payload)
        if response.status_code == 200:
            players_data = response.json().get('players', [])
            for player_data in players_data:
                player_data['slate_id'] = slate_id
                all_players_data.append(player_data)
        else:
            print(f"Failed to get projections for slate {slate_id}: {response.text}")

    all_players_df = pd.DataFrame(all_players_data)
    # Combine away_team + home_team into a enw column named "matchup"
    all_players_df['matchup'] = all_players_df['team'] + " vs " + all_players_df['opp']
    columns_to_keep = [
        'name', 'position', 'team', 'opp', 'minutes', 'possessions','fd_points', 'points', 'assists', 'rebounds', 'offensive_rebounds', 
        'defensive_rebounds', 'blocks', 'steals', 'fouls', 'turnovers','two_pt_attempts', 'two_pt_fg', 'three_pt_attempts', 'three_pt_fg', 
        'free_throw_attempts', 'free_throws_made', 'roster_pos', 'confirmed', 'double_doubles','triple_doubles', 'injury', 'site', 'fd_std', 
        'fd_25_percentile', 'fd_50_percentile', 'fd_75_percentile', 'fd_85_percentile', 'fd_95_percentile', 'fd_99_percentile', 'timestamp', 
        'date', 'slate_id', 'gid', 'matchup'
    ]

    all_players_df = all_players_df[columns_to_keep]
    all_players_df['effective_fg_percentage'] = ((all_players_df['two_pt_fg'] + all_players_df['three_pt_fg']) + 0.5 * all_players_df['three_pt_fg']) / (all_players_df['two_pt_attempts'] + all_players_df['three_pt_attempts']) * 100
    all_players_df.rename(columns={'name': 'player_names'}, inplace=True)
    all_players_df = all_players_df.drop_duplicates(subset='player_names')
    csv_file_path = 'all_players_df.csv'
    #all_players_df.to_csv(csv_file_path, index=False)
    return all_players_df