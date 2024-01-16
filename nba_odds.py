import requests
import pandas as pd
import logging
from dotenv import load_dotenv
import os


# Initialize logging for debugging and error tracking
logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()
ODDS_API_KEY = os.getenv('ODDS_API_KEY')

# Constants for API requests
HEADERS = {'accept': 'application/json'}
BASE_URL = "https://api.the-odds-api.com/v4"

# Enhanced API request function with specific error handling
def make_api_request(url):
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except requests.ConnectionError:
        logging.error("Connection error occurred")
    except requests.Timeout:
        logging.error("Request timed out")
    except requests.HTTPError as http_err:
        logging.error(f"HTTP error occurred: {http_err}")
    except Exception as err:
        logging.error(f"An error occurred: {err}")
    return None

# Utility function to construct URLs for different endpoints
def construct_url(endpoint, params):
    return f"{BASE_URL}/{endpoint}?{'&'.join([f'{k}={v}' for k, v in params.items()])}&apiKey={ODDS_API_KEY}"

# Function to fetch game IDs for NBA games
def fetch_nba_game_ids():
    url = construct_url("sports/basketball_nba/odds", {"regions": "us", "markets": "h2h", "dateFormat": "iso", "oddsFormat": "decimal"})
    response = make_api_request(url)
    return [game['id'] for game in response] if response else []

# Converts Decimal Odds into US Odds
def convert_decimal_to_us_odds(decimal_odds):
    # Handling the edge case where decimal odds are exactly 1
    if decimal_odds == 1:
        return 0

    if decimal_odds >= 2.00:
        us_odds = (decimal_odds - 1) * 100
    else:
        us_odds = -100 / (decimal_odds - 1)
    
    return int(us_odds)

# Function to fetch player prop odds for given game IDs and convert to DataFrame
def fetch_nba_player_odds(game_ids, save_to_csv=True, csv_path='player_odds.csv'):
    dfs = []  # List to store individual DataFrames
    for game_id in game_ids:
        url = construct_url(f"sports/basketball_nba/events/{game_id}/odds", 
                            {"regions": "us", "markets": ",".join([
                             "player_points", "player_points_alternate", "player_rebounds", "player_rebounds_alternate", "player_assists",
                             "player_assists_alternate", "player_threes", "player_threes_alternate", "player_blocks",
                             "player_blocks_alternate", "player_steals", "player_steals_alternate", "player_turnovers"]),
                             "dateFormat": "iso", "oddsFormat": "decimal", "bookmakers": "fanduel"})
        response = make_api_request(url)
        if response and 'bookmakers' in response:
            odds_list = [[bookmaker['key'], market['key'], outcome['name'], outcome['description'], outcome['price'], outcome['point']]
                         for bookmaker in response['bookmakers']
                         for market in bookmaker['markets']
                         for outcome in market['outcomes']
                         if 'point' in outcome]
            df = pd.DataFrame(odds_list, columns=['bookmaker', 'market', 'outcome', 'description', 'price', 'point'])
            dfs.append(df)
    final_df = pd.concat([df for df in dfs if not df.empty])
    final_df.rename(columns={'description': 'player_names', 'price': 'odds', 'point': 'stat_threshold',
                             'bookmaker': 'sports_book', 'market': 'bet_type', 'outcome': 'over/under'}, inplace=True)
    final_df['player_names'] = final_df['player_names'].str.replace('.', '').str.replace('-', ' ')
    
    # Add 'us_odds' column
    final_df['us_odds'] = final_df['odds'].apply(convert_decimal_to_us_odds)
    if save_to_csv:
        final_df.to_csv(csv_path, index=False)
    return final_df

