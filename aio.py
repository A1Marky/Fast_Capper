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
ODDS_API_BASE_URL = "https://api.the-odds-api.com/v4"

# Initialize logging for debugging and error tracking
logging.basicConfig(level=logging.INFO)

def make_post_request(url, payload):
    try:
        response = session.post(url, data=json.dumps(payload))
        response.raise_for_status()
        logging.info("Response from POST request: %s", response.json())  # For debugging
        return response.json()
    except RequestException as e:
        logging.error(f"Request failed: {e}")
        return None

def get_auth_token(email: str, password: str) -> str:
    payload = {
        "returnSecureToken": True,
        "email": email,
        "password": password
    }
    url = AUTH_URL + SABERSIM_API_KEY
    response_data = make_post_request(url, payload)
    if response_data and "idToken" in response_data:
        return response_data["idToken"]
    else:
        error_message = response_data.get("error", {}).get("message", "Unknown error") if response_data else "No response"
        logging.error(f"Failed to get auth token: {error_message}")
        return None

def get_games_data(auth_token: str, date: str) -> pd.DataFrame:
    base_url = "https://basketball-sim.appspot.com/_ah/api/nba/v1/games"
    url = f"{base_url}?date={date}&site=fd&sport=nba"
    session.headers.update({'Authorization': f'Bearer {auth_token}'})
    try:
        response = session.get(url)
        response.raise_for_status()
        logging.info("Response from games data: %s", response.json())  # For debugging
        games_data = response.json().get('games', [])
    except RequestException as e:
        logging.error(f"Failed to get games data: {e}")
        return pd.DataFrame()

    games_df = pd.DataFrame(games_data)
    game_data_columns_to_keep = [
        'away_score', 'away_team', 'away_wins', 'home_score', 'home_team', 'home_wins', 'start_time_js', 'gid'
    ]
    games_df = games_df[game_data_columns_to_keep]
    games_df['start_time_js'] = pd.to_datetime(games_df['start_time_js'], utc=True)
    eastern_zone = pytz.timezone('US/Eastern')
    games_df['start_time_et'] = games_df['start_time_js'].dt.tz_convert(eastern_zone)
    games_df['start_time_readable'] = games_df['start_time_et'].dt.strftime('%Y-%m-%d %I:%M %p ET')
    # Save the player_projections_df to CSV
    csv_file_path = 'games_data.csv'
    games_df.to_csv(csv_file_path, index=False)
    return games_df
    

def get_slates(auth_token: str, date: str, sport: str = 'nba') -> list:
    url = f"https://basketball-sim.appspot.com/_ah/api/nba/v1/slates?date={date}&sport={sport}"
    session.headers.update({'Authorization': f'Bearer {auth_token}'})
    try:
        response = session.get(url)
        response.raise_for_status()
        response_data = response.json()
        logging.info("Response from slates data: %s", response_data)  # For debugging
    except RequestException as e:
        logging.error(f"Failed to get slates: {e}")
        return []
    if response.status_code == 200 and 'slates' in response_data:
        return [slate.get('id') for slate in response_data['slates'] if slate.get('site').lower() == 'fd']
    else:
        logging.error("Failed to get slates: HTTP " + str(response.status_code))
        return []

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
            logging.error(f"Failed to get projections for slate {slate_id}: {e}")

    player_projections_df = pd.DataFrame(player_projections_data)
    projection_columns_to_keep = [
        'name', 'position', 'team', 'opp', 'minutes', 'possessions', 'fd_points', 'points', 'assists', 'rebounds', 
        'offensive_rebounds', 'defensive_rebounds', 'blocks', 'steals', 'fouls', 'turnovers', 'two_pt_attempts', 
        'two_pt_fg', 'three_pt_attempts', 'three_pt_fg', 'free_throw_attempts', 'free_throws_made', 'roster_pos', 
        'confirmed', 'double_doubles', 'triple_doubles', 'injury', 'site', 'fd_std', 'fd_25_percentile', 
        'fd_50_percentile', 'fd_75_percentile', 'fd_85_percentile', 'fd_95_percentile', 'fd_99_percentile', 
        'timestamp', 'date', 'slate_id', 'gid'
    ]
    player_projections_df = player_projections_df[projection_columns_to_keep]
    player_projections_df.rename(columns={'name': 'player_names'}, inplace=True)
    player_projections_df = player_projections_df.drop_duplicates(subset='player_names')
    return player_projections_df

# Functions for getting player odds data
def make_api_request(url):
    try:
        response = requests.get(url, headers={'accept': 'application/json'})
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Request error occurred: {e}")
        return None

def construct_url(endpoint, params, odds_api_key):
    full_url = f"{ODDS_API_BASE_URL}/{endpoint}"
    param_str = '&'.join([f'{key}={value}' for key, value in params.items()])
    return f"{full_url}?{param_str}&apiKey={odds_api_key}"


def fetch_nba_game_ids(odds_api_key):
    endpoint = "sports/basketball_nba/odds"
    params = {"regions": "us", "markets": "h2h", "dateFormat": "iso", "oddsFormat": "decimal"}
    url = construct_url(endpoint, params, odds_api_key)
    response = make_api_request(url)
    return [game['id'] for game in response] if response else []

def convert_decimal_to_us_odds(decimal_odds):
    if decimal_odds == 1:
        return 0
    return int((decimal_odds - 1) * 100) if decimal_odds >= 2.00 else int(-100 / (decimal_odds - 1))

def fetch_nba_player_odds(game_ids, odds_api_key, save_to_csv=True, csv_path='player_odds.csv'):
    dfs = []
    for game_id in game_ids:
        endpoint = f"sports/basketball_nba/events/{game_id}/odds"
        markets = ["player_points", "player_points_alternate", "player_rebounds", "player_rebounds_alternate",
                   "player_assists", "player_assists_alternate", "player_threes", "player_threes_alternate",
                   "player_blocks", "player_blocks_alternate", "player_steals", "player_steals_alternate",
                   "player_turnovers"]
        params = {"regions": "us", "markets": ",".join(markets), "dateFormat": "iso", "oddsFormat": "decimal",
                  "bookmakers": "draftkings"}
        url = construct_url(endpoint, params, odds_api_key)
        response = make_api_request(url)
        if response and 'bookmakers' in response:
            odds_data = [[bookmaker['key'], market['key'], outcome['name'], outcome['description'], outcome['price'], outcome['point']]
                         for bookmaker in response['bookmakers']
                         for market in bookmaker['markets']
                         for outcome in market['outcomes']
                         if 'point' in outcome]
            df = pd.DataFrame(odds_data, columns=['bookmaker', 'market', 'outcome', 'description', 'price', 'point'])
            if not df.empty:
                dfs.append(df)

    if dfs:
        final_df = pd.concat(dfs, ignore_index=True)
        final_df.rename(columns={'description': 'player_names', 'price': 'odds', 'point': 'stat_threshold',
                                 'bookmaker': 'sports_book', 'market': 'bet_type', 'outcome': 'over/under'}, inplace=True)
        final_df['player_names'] = final_df['player_names'].str.replace(r'[.-]', ' ', regex=True)
        final_df['us_odds'] = final_df['odds'].apply(convert_decimal_to_us_odds)
        filtered_odds_df = final_df[final_df['us_odds'] > -300]
        if save_to_csv:
            filtered_odds_df.to_csv(csv_path, index=False)
        return filtered_odds_df
    return pd.DataFrame()


# Define the calculate_edge function for calculating the edge value
def calculate_edge(row):
    bet_type = row['bet_type']
    over_under = row['over/under']
    stat_value = None

    if bet_type in ['player_assists', 'player_assists_alternate']:
        stat_value = row['assists']
    elif bet_type in ['player_points', 'player_points_alternate']:
        stat_value = row['points']
    elif bet_type in ['player_rebounds', 'player_rebounds_alternate']:
        stat_value = row['rebounds']
    elif bet_type in ['player_threes', 'player_threes_alternate']:
        stat_value = row['three_pt_fg']
    elif bet_type in ['player_blocks', 'player_blocks_alternate']:
        stat_value = row['blocks']
    elif bet_type in ['player_steals', 'player_steals_alternate']:
        stat_value = row['steals']

    if stat_value is not None:
        return (stat_value - row['stat_threshold']) if over_under == 'Over' else (row['stat_threshold'] - stat_value)
    else:
        return None
    


def main():
    st.title("NBA Game Data Analysis App")

    with st.sidebar:
        st.header("User Authentication")
        email = st.text_input("Email", value=DEFAULT_EMAIL)
        password = st.text_input("Password", type="password", value=DEFAULT_PASSWORD)

        st.header("Odds API Key")
        user_provided_odds_api_key = st.text_input("Enter Odds API Key (optional)", value="")

        st.header("Select Date")
        selected_date = st.date_input("Date", datetime.now())

    # Use user-provided key if available, else use the one from .env
    active_odds_api_key = user_provided_odds_api_key if user_provided_odds_api_key else ODDS_API_KEY

    if st.sidebar.button("Fetch Data"):
        auth_token = get_auth_token(email, password)
        if auth_token:
            try:
                games_df = get_games_data(auth_token, selected_date.strftime('%Y-%m-%d'))
                slates = get_slates(auth_token, selected_date.strftime('%Y-%m-%d'))
                player_projections_df = get_player_projections(auth_token, selected_date.strftime('%Y-%m-%d'), slates)
                
                # Fetch and process odds data
                game_ids = fetch_nba_game_ids(active_odds_api_key)
                odds_df = fetch_nba_player_odds(game_ids, active_odds_api_key, save_to_csv=True, csv_path='player_odds.csv')

                master_df = pd.merge(player_projections_df, odds_df, on='player_names', how='right')
                master_df = master_df.dropna(subset=['team'])
                master_df['edge'] = master_df.apply(calculate_edge, axis=1)
                master_df = master_df[master_df['edge'] >= 1]
                master_df = master_df.sort_values(by='edge', ascending=False)
                # Save the master dataframe to a CSV file
                master_df.to_csv('master_df.csv', index=False)
                
                st.write("Games Data:", games_df)
                st.write("Master Dataframe:", master_df)
                
            except Exception as e:
                st.error(f"An error occurred: {e}")
        else:
            st.error("Authentication failed.")

if __name__ == "__main__":
    main()

