import streamlit as st
import pandas as pd
import requests
import json
import os
from datetime import datetime
from dotenv import load_dotenv
from requests.exceptions import RequestException
import logging
import pytz

# Load environment variables
load_dotenv()
SABERSIM_API_KEY = os.getenv('SABERSIM_API_KEY')
ODDS_API_KEY = os.getenv('ODDS_API_KEY')
DEFAULT_EMAIL = os.getenv('SABERSIM_EMAIL')
DEFAULT_PASSWORD = os.getenv('SABERSIM_PASSWORD')

# Initialize a session to improve performance by reusing TCP connections
session = requests.Session()
# Default headers used for all requests in the session
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Content-Type': 'application/json',
    'Accept': 'application/json, text/plain, */*'
})

# Define the base URLs
AUTH_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key="
BASE_URL = "https://api.the-odds-api.com/v4"

# Initialize logging for debugging and error tracking
logging.basicConfig(level=logging.INFO)

# Define the make_post_request function
def make_post_request(url, payload):
    try:
        response = session.post(url, data=json.dumps(payload))
        response.raise_for_status()
        print("Response from POST request:", response.json())  # For debugging
        return response.json()
    except RequestException as e:
        raise Exception(f"Request failed: {e}")

# Define the get_auth_token function
def get_auth_token(email: str, password: str) -> str:
    payload = {
        "returnSecureToken": True,
        "email": email,
        "password": password
    }
    url = AUTH_URL + SABERSIM_API_KEY
    response_data = make_post_request(url, payload)
    if "idToken" in response_data:
        return response_data["idToken"]
    else:
        error_message = response_data.get("error", {}).get("message", "Unknown error")
        raise Exception(f"Failed to get auth token: {error_message}")

# Define the get_games_data function
def get_games_data(auth_token: str, date: str) -> pd.DataFrame:
    base_url = "https://basketball-sim.appspot.com/_ah/api/nba/v1/games"
    url = f"{base_url}?date={date}&site=fd&sport=nba"
    session.headers.update({'Authorization': f'Bearer {auth_token}'})
    try:
        response = session.get(url)
        response.raise_for_status()
        print("Response from games data:", response.json())  # For debugging
        games_data = response.json().get('games', [])
    except RequestException as e:
        raise Exception(f"Failed to get games data: {e}")
    games_df = pd.DataFrame(games_data).drop_duplicates(subset=['gid'])
    return games_df

# Define the get_slates function
def get_slates(auth_token: str, date: str, sport: str = 'nba') -> list:
    url = f"https://basketball-sim.appspot.com/_ah/api/nba/v1/slates?date={date}&sport={sport}"
    session.headers.update({'Authorization': f'Bearer {auth_token}'})
    try:
        response = session.get(url)
        response.raise_for_status()
        response_data = response.json()
    except RequestException as e:
        raise Exception(f"Failed to get slates: {e}")
    if response.status_code == 200 and 'slates' in response_data:
        slates_list = [slate.get('id') for slate in response_data['slates'] if slate.get('site').lower() == 'fd']
        return slates_list
    else:
        raise Exception("Failed to get slates: HTTP " + str(response.status_code))

# Define the get_player_projections function
def get_player_projections(auth_token: str, date: str, slate_ids: list, sport: str = 'nba', site: str = 'fd') -> pd.DataFrame:
    url = "https://basketball-sim.appspot.com/endpoints/get_player_projections"
    session.headers.update({'Authorization': f'Bearer {auth_token}'})
    player_projections_data = []
    for slate_id in slate_ids:
        payload = {
            "conditionals": [],
            "date": date,
            "percentile": "0",
            "site": site,
            "slate": slate_id,
            "sport": sport
        }
        try:
            response = session.post(url, json=payload)
            response.raise_for_status()
            players_data = response.json().get('players', [])
            for player_data in players_data:
                player_data['slate_id'] = slate_id
                player_projections_data.append(player_data)
        except RequestException as e:
            print(f"Failed to get projections for slate {slate_id}: {e}")

    # Create the DataFrame outside the loop
    player_projections_df = pd.DataFrame(player_projections_data)
    return player_projections_df

''' The below section is where the functions will be called'''
# Get the current date in YYYY-MM-DD format
current_date = datetime.now().strftime('%Y-%m-%d')
# Call the get_auth_token function to get the auth token
auth_token = get_auth_token(DEFAULT_EMAIL, DEFAULT_PASSWORD)
# Call the get_games_data function to get the games data
games_df = get_games_data(auth_token, current_date)
# Call the get_slates function to get the slates
slates = get_slates(auth_token, current_date)
# Call the get_player_projections function to get the player projections
player_projections_df = get_player_projections(auth_token, current_date, slates)

''' The Section below is the start of DataFrame Data Processing and structure building for player projections'''
# Define columns to keep in the player projections DataFrame
projection_columns_to_keep = [
    'name', 'position', 'team', 'opp', 'minutes', 'possessions', 'fd_points', 'points', 'assists', 'rebounds', 
    'offensive_rebounds', 'defensive_rebounds', 'blocks', 'steals', 'fouls', 'turnovers', 'two_pt_attempts', 
    'two_pt_fg', 'three_pt_attempts', 'three_pt_fg', 'free_throw_attempts', 'free_throws_made', 'roster_pos', 
    'confirmed', 'double_doubles', 'triple_doubles', 'injury', 'site', 'fd_std', 'fd_25_percentile', 
    'fd_50_percentile', 'fd_75_percentile', 'fd_85_percentile', 'fd_95_percentile', 'fd_99_percentile', 
    'timestamp', 'date', 'slate_id', 'gid'
]

# Filter the DataFrame to include only the defined columns and remove duplicates
player_projections_df = player_projections_df[projection_columns_to_keep]
player_projections_df.rename(columns={'name': 'player_names'}, inplace=True)
player_projections_df = player_projections_df.drop_duplicates(subset='player_names')

# Save the player_projections_df to CSV
csv_file_path = 'player_projections.csv'
player_projections_df.to_csv(csv_file_path, index=False)


''' The Section below is the start of DataFrame Data Processing and structure building for game_data'''
# Define columns to keep in the game data DataFrame
game_data_columns_to_keep = [
    'away_score', 'away_team', 'away_wins', 'home_score','home_team', 'home_wins', 'start_time_js', 'gid'
]
# Filter the games DataFrame to include only the defined columns
games_df = games_df[game_data_columns_to_keep]
# Convert to datetime and then to Eastern Time
games_df['start_time_js'] = pd.to_datetime(games_df['start_time_js'], utc=True)
# Convert from UTC to Eastern Time
eastern_zone = pytz.timezone('US/Eastern')
games_df['start_time_et'] = games_df['start_time_js'].dt.tz_convert(eastern_zone)
# Format the datetime to a more readable format
games_df['start_time_readable'] = games_df['start_time_et'].dt.strftime('%Y-%m-%d %I:%M %p ET')

# Save the player_projections_df to CSV
csv_file_path = 'games_data.csv'
games_df.to_csv(csv_file_path, index=False)