import requests
import pandas as pd
import logging
from dotenv import load_dotenv
import os

# Initialize logging for debugging and error tracking
logging.basicConfig(level=logging.INFO)

# Load environment variables from a .env file for security and flexibility
load_dotenv()
ODDS_API_KEY = os.getenv('ODDS_API_KEY')  # Retrieve the API key from the environment variables

# Constants for API requests
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
        if save_to_csv:
            final_df.to_csv(csv_path, index=False)  # Save DataFrame to CSV if required
        return final_df
    return pd.DataFrame()

# Example usage
game_ids = fetch_nba_game_ids()
odds_df = fetch_nba_player_odds(game_ids)
#print(odds_df.head())
