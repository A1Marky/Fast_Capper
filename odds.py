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

# Common function to make API requests
def make_api_request(url, headers):
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"API Request Error: {e}")
        return None

# Function to fetch game IDs for NBA games
def fetch_nba_game_ids():
    url = f"https://api.the-odds-api.com/v4/sports/basketball_nba/odds?apiKey={ODDS_API_KEY}&regions=us&markets=h2h&dateFormat=iso&oddsFormat=decimal"
    headers = {'accept': 'application/json'}
    response = make_api_request(url, headers)
    return [game['id'] for game in response] if response else []

# Function to fetch player prop odds for given game IDs and convert to DataFrame
def fetch_nba_player_odds(game_ids, save_to_csv=True, csv_path='playerprop_odds_nba.csv'):
    base_url = "https://api.the-odds-api.com/v4"
    dfs = []  # List to store individual DataFrames
    for game_id in game_ids:
        url = f"{base_url}/sports/basketball_nba/events/{game_id}/odds?apiKey={ODDS_API_KEY}&regions=us&markets=player_points,player_rebounds,player_assists,player_threes,player_double_double,player_blocks,player_steals,player_turnovers,player_points_rebounds_assists,player_points_rebounds,player_points_assists,player_rebounds_assists&dateFormat=iso&oddsFormat=decimal&bookmakers=fanduel"
        headers = {'accept': 'application/json'}
        response = make_api_request(url, headers)
        if response and 'bookmakers' in response:
            odds_list = []
            for bookmaker in response['bookmakers']:
                for market in bookmaker['markets']:
                    for outcome in market['outcomes']:
                        if 'point' in outcome:
                            odds_list.append([bookmaker['key'], market['key'], outcome['name'], outcome['description'], outcome['price'], outcome['point']])
            df = pd.DataFrame(odds_list, columns=['bookmaker', 'market', 'outcome', 'description', 'price', 'point'])
            dfs.append(df)
    final_df = pd.concat([df for df in dfs if not df.empty])
    final_df.rename(columns={'description': 'player_names', 'price': 'odds', 'point': 'stat_threshold', 'bookmaker': 'sports_book', 'market': 'bet_type', 'outcome': 'over/under'}, inplace=True)
    final_df['player_names'] = final_df['player_names'].str.replace('.', '').str.replace('-', ' ')
    if save_to_csv:
        final_df.to_csv(csv_path, index=False)
    return final_df

# Function to merge SaberSim projections (filtered_df) with odds data (final_df)
def merge_sabersim_and_odds_data(filtered_df, final_df, csv_path='optimizer_data.csv'):
    # Assuming the common column for merging is 'player_names' in final_df and a similar column in filtered_df
    # The column name in filtered_df should be adjusted based on the actual structure of the dataframe in app.py
    common_column = 'player_names'  # Replace with the actual common column name in filtered_df
    merged_df = pd.merge(filtered_df, final_df, how='inner', left_on=common_column, right_on='player_names')
    merged_df.to_csv(csv_path, index=False)
    return merged_df

