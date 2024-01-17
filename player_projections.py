import requests
import json
import os
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
from decimal import Decimal

# Load environment variables
load_dotenv()

# Retrieve API key from environment variables
SABERSIM_API_KEY = os.getenv('SABERSIM_API_KEY')

def get_auth_token(email: str, password: str) -> str:
    """
    Authenticate and retrieve an auth token using email and password.
    Raises an exception if authentication fails.
    """
    # Constructing the URL for authentication
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={SABERSIM_API_KEY}"
    
    # Prepare the payload for the POST request
    payload = json.dumps({
        "returnSecureToken": True,
        "email": email,
        "password": password
    })
    
    # Set headers for the request
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    }
    
    # Making the POST request to get the auth token
    response = requests.post(url, headers=headers, data=payload)
    response_data = response.json()
    
    # Check if the response is successful
    if response.status_code == 200:
        return response_data.get("idToken")
    raise Exception("Failed to get auth token: " + response_data.get("error", {}).get("message", ""))

def get_slates(auth_token: str, date: str, sport: str = 'nba') -> list:
    """
    Retrieve slates based on the given date and sport.
    Raises an exception if the request fails.
    """
    # Constructing the URL for the GET request
    url = f"https://basketball-sim.appspot.com/_ah/api/nba/v1/slates?date={date}&sport={sport}"
    
    # Set headers for the request
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {auth_token}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    }
    
    # Making the GET request to retrieve slates
    response = requests.get(url, headers=headers)
    response_data = response.json()
    
    # Processing the response data
    if response.status_code == 200 and isinstance(response_data, dict) and 'slates' in response_data:
        slates_list = [slate.get('id') for slate in response_data.get('slates', []) if slate.get('site').lower() == 'fd']
        return slates_list
    
    raise Exception("Failed to get slates: HTTP " + str(response.status_code))

def get_player_projections(auth_token: str, date: str, slate_ids: list, sport: str = 'nba', site: str = 'fd') -> pd.DataFrame:
    """
    Retrieve player projections for given slates, sport, and site.
    Converts the response data into a pandas DataFrame and saves it as CSV.
    """
    # URL for getting player projections
    url = "https://basketball-sim.appspot.com/endpoints/get_player_projections"
    
    # Set headers for the request
    headers = {
        'Authorization': f'Bearer {auth_token}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/plain, */*',
    }

    all_players_data = []
    for slate_id in slate_ids:
        # Prepare payload for each slate
        payload = json.dumps({
            "conditionals": [],
            "date": date,
            "percentile": "0",
            "site": site,
            "slate": slate_id,
            "sport": sport
        })

        # Making the POST request for each slate
        response = requests.post(url, headers=headers, data=payload)
        if response.status_code == 200:
            players_data = response.json().get('players', [])
            # Append slate_id to each player's data
            for player_data in players_data:
                player_data['slate_id'] = slate_id
                all_players_data.append(player_data)
        else:
            print(f"Failed to get projections for slate {slate_id}: {response.text}")

    # Convert the aggregated data into a DataFrame
    all_players_df = pd.DataFrame(all_players_data)
    # Combine away_team + home_team into a new column named "matchup"
    all_players_df['matchup'] = all_players_df['team'] + " vs " + all_players_df['opp']
    
    # Define columns to keep in the DataFrame
    columns_to_keep = [
        'name', 'position', 'team', 'opp', 'minutes', 'possessions', 'fd_points', 'points', 'assists', 'rebounds', 
        'offensive_rebounds', 'defensive_rebounds', 'blocks', 'steals', 'fouls', 'turnovers', 'two_pt_attempts', 
        'two_pt_fg', 'three_pt_attempts', 'three_pt_fg', 'free_throw_attempts', 'free_throws_made', 'roster_pos', 
        'confirmed', 'double_doubles', 'triple_doubles', 'injury', 'site', 'fd_std', 'fd_25_percentile', 
        'fd_50_percentile', 'fd_75_percentile', 'fd_85_percentile', 'fd_95_percentile', 'fd_99_percentile', 
        'timestamp', 'date', 'slate_id', 'gid', 'matchup'
    ]

    # Filter the DataFrame to include only the defined columns and remove duplicates
    all_players_df = all_players_df[columns_to_keep]
    all_players_df.rename(columns={'name': 'player_names'}, inplace=True)
    all_players_df = all_players_df.drop_duplicates(subset='player_names')
    
    # Save the DataFrame to CSV
    csv_file_path = 'player_projections.csv'
    all_players_df.to_csv(csv_file_path, index=False)
    
    return all_players_df


# Gets all the Schedule and Game Data
def get_games_data(auth_token: str, date: str, slates_list: list) -> pd.DataFrame:
    """
    Retrieve game data for each slate in the slates_list and return as a DataFrame with unique 'gid' rows.
    """
    all_games_data = []
    base_url = "https://basketball-sim.appspot.com/_ah/api/nba/v1/games"

    # Common headers for the requests
    headers = {
        'Authorization': f'Bearer {auth_token}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/plain, */*',
    }

    for slate_id in slates_list:
        url = f"{base_url}?date={date}&site=fd&slate={slate_id}&sport=nba"
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            games_data = response.json().get('games', [])
            all_games_data.extend(games_data)
        else:
            print(f"Failed to get games data for slate {slate_id}: {response.text}")

    # Create a DataFrame from the aggregated games data
    games_df = pd.DataFrame(all_games_data)

    # Remove duplicate rows based on the 'gid' column
    games_df = games_df.drop_duplicates(subset=['gid'])

    return games_df

# Example usage
# auth_token = get_auth_token('email@example.com', 'password')
# slates_list = get_slates(auth_token, '2024-01-17')
# games_df = get_games_data(auth_token, '2024-01-17', slates_list)
