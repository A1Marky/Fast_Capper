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


''' The below section below are the functions for getting player odds data'''
# Constants for Odds API requests
HEADERS = {'accept': 'application/json'}  # Standard header for JSON responses
BASE_URL = "https://api.the-odds-api.com/v4"  # Base URL for the API requests


def make_api_request(url):
    """ 
    Make a GET request to a specified URL and return the JSON response.
    Includes error handling for various types of request failures.
    """
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Request error occurred: {e}")  # Log any request-related errors
    return None

def construct_url(endpoint, params):
    """
    Construct the full URL for an API request using the endpoint and parameters.
    Appends the API key to the URL.
    """
    full_url = f"{BASE_URL}/{endpoint}"
    param_str = '&'.join([f'{key}={value}' for key, value in params.items()])
    return f"{full_url}?{param_str}&apiKey={ODDS_API_KEY}"

def fetch_nba_game_ids():
    """
    Fetch the game IDs for NBA games using the API.
    Returns a list of game IDs if successful, or an empty list otherwise.
    """
    endpoint = "sports/basketball_nba/odds"
    params = {"regions": "us", "markets": "h2h", "dateFormat": "iso", "oddsFormat": "decimal"}
    url = construct_url(endpoint, params)
    response = make_api_request(url)
    return [game['id'] for game in response] if response else []

def convert_decimal_to_us_odds(decimal_odds):
    """
    Convert decimal odds to US odds format.
    Handles special cases where decimal odds are 1 or greater than/equal to 2.
    """
    if decimal_odds == 1:
        return 0
    return int((decimal_odds - 1) * 100) if decimal_odds >= 2.00 else int(-100 / (decimal_odds - 1))

def fetch_nba_player_odds(game_ids, save_to_csv=True, csv_path='player_odds.csv'):
    """
    Fetch player prop odds for given NBA game IDs and convert the data to a DataFrame.
    Optionally saves the DataFrame to a CSV file.
    """
    dfs = []  # List to store DataFrames for each game
    for game_id in game_ids:
        # Construct URL for each game's odds
        endpoint = f"sports/basketball_nba/events/{game_id}/odds"
        markets = ["player_points", "player_points_alternate", "player_rebounds", "player_rebounds_alternate",
                   "player_assists", "player_assists_alternate", "player_threes", "player_threes_alternate",
                   "player_blocks", "player_blocks_alternate", "player_steals", "player_steals_alternate",
                   "player_turnovers"]
        params = {"regions": "us", "markets": ",".join(markets), "dateFormat": "iso", "oddsFormat": "decimal",
                  "bookmakers": "fanduel"}
        url = construct_url(endpoint, params)
        response = make_api_request(url)

        # Process the response and construct DataFrame
        if response and 'bookmakers' in response:
            odds_data = [[bookmaker['key'], market['key'], outcome['name'], outcome['description'], outcome['price'], outcome['point']]
                         for bookmaker in response['bookmakers']
                         for market in bookmaker['markets']
                         for outcome in market['outcomes']
                         if 'point' in outcome]
            df = pd.DataFrame(odds_data, columns=['bookmaker', 'market', 'outcome', 'description', 'price', 'point'])
            dfs.append(df)

    # Combine all DataFrames into one and perform final transformations
    if dfs:
        final_df = pd.concat(dfs, ignore_index=True)
        final_df.rename(columns={'description': 'player_names', 'price': 'odds', 'point': 'stat_threshold',
                                 'bookmaker': 'sports_book', 'market': 'bet_type', 'outcome': 'over/under'}, inplace=True)
        final_df['player_names'] = final_df['player_names'].str.replace(r'[.-]', ' ', regex=True)  # Clean up player names
        final_df['us_odds'] = final_df['odds'].apply(convert_decimal_to_us_odds)  # Convert odds to US format
        
        # Filter the DataFrame
        filtered_odds_df = final_df[final_df['us_odds'] > -400]
        
        if save_to_csv:
            filtered_odds_df.to_csv(csv_path, index=False)  # Save DataFrame to CSV if required
        return filtered_odds_df
    return pd.DataFrame()


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
# Call the fetch_nba_game_ids function to get the game IDs for the player odds
game_ids = fetch_nba_game_ids()
# Call the fetch_nba_player_odds function to get the player odds
odds_df = fetch_nba_player_odds(game_ids)
# Call the master dataframe that includes player projections and player odds
master_df = pd.merge(player_projections_df,odds_df, on='player_names', how='right')
master_df.to_csv('master_df.csv', index=False)



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

''' The Section below is the start of DataFrame Data Processing and structure building for game_data'''