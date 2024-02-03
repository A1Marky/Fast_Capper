# Optimization of the provided sports and odds information fetching script

import argparse
import requests
import pandas as pd

# Constants and Configuration
BASE_URL = 'https://api.the-odds-api.com/v4'
SPORT = 'basketball_nba'
REGIONS = 'us'
ODDS_FORMAT = 'american'
DATE_FORMAT = 'iso'
BOOKMAKERS = 'draftkings'
PLAYER_MARKETS = ("player_points,player_points_alternate,player_rebounds,"
                  "player_rebounds_alternate,player_assists,player_assists_alternate,"
                  "player_threes,player_threes_alternate,player_double_double,"
                  "player_blocks,player_blocks_alternate,player_steals,"
                  "player_steals_alternate,player_points_rebounds_assists,"
                  "player_points_rebounds,player_points_assists,player_rebounds_assists")

def parse_command_line_arguments():
    """Parse command line arguments for the API key."""
    parser = argparse.ArgumentParser(description='Fetch Sports and Odds Information')
    parser.add_argument('--api-key', type=str, required=True, help='API key for accessing the Odds API')
    args = parser.parse_args()
    return args.api_key

def api_request(url, params):
    """Make an API request and return the JSON response."""
    response = requests.get(url, params=params)
    response.raise_for_status()  # Will raise an exception for 4XX and 5XX status codes
    return response.json()

def fetch_game_ids(api_key):
    """Fetch a list of live & upcoming game IDs."""
    odds_url = f'{BASE_URL}/sports/{SPORT}/odds'
    params = {
        'api_key': api_key,
        'regions': REGIONS,
        'oddsFormat': ODDS_FORMAT,
        'dateFormat': DATE_FORMAT,
        'bookmakers': BOOKMAKERS
    }
    odds_data = api_request(odds_url, params)
    return [event['id'] for event in odds_data]

def decimal_to_american(decimal_odds):
    """Convert decimal odds to American odds format."""
    if decimal_odds >= 2.0:
        return int((decimal_odds - 1) * 100)
    else:
        return int(-100 / (decimal_odds - 1))

def fetch_nba_player_odds(api_key, game_ids):
    """Fetch NBA player odds and return a DataFrame."""
    collected_odds = []
    for game_id in game_ids:
        odds_url = f"{BASE_URL}/sports/{SPORT}/events/{game_id}/odds"
        params = {
            'apiKey': api_key,
            'regions': REGIONS,
            'markets': PLAYER_MARKETS,
            'dateFormat': DATE_FORMAT,
            'oddsFormat': 'decimal',
            'bookmakers': BOOKMAKERS
        }
        response_data = api_request(odds_url, params)
        for bookmaker in response_data.get('bookmakers', []):
            for market in bookmaker.get('markets', []):
                for outcome in market.get('outcomes', []):
                    collected_odds.append([
                        bookmaker['key'], market['key'], outcome['name'],
                        outcome.get('description', ''), outcome['price'],
                        outcome.get('point', '')
                    ])
    
    columns = ['bookmaker', 'market', 'outcome', 'description', 'price', 'point']
    player_odds_df = pd.DataFrame(collected_odds, columns=columns)
    if not player_odds_df.empty:
        player_odds_df = process_odds_dataframe(player_odds_df)
    return player_odds_df

def process_odds_dataframe(df):
    """Process and convert odds DataFrame."""
    rename_map = {
        'description': 'player_names', 'price': 'odds',
        'point': 'stat_threshold', 'bookmaker': 'sports_book',
        'market': 'bet_type', 'outcome': 'over/under'
    }
    df.rename(columns=rename_map, inplace=True)
    df['player_names'] = df['player_names'].str.replace('.', '').str.replace('-', ' ')
    df['american_odds'] = df['odds'].apply(decimal_to_american)
    return df[['player_names', 'bet_type', 'over/under', 'stat_threshold', 'odds', 'american_odds', 'sports_book']]

def save_to_csv(df, path='player_odds.csv'):
    """Save DataFrame to a CSV file."""
    if not df.empty:
        df.to_csv(path, index=False)

def main():
    api_key = "a2a3265fc28e6a9e6e26384519169a10"
    game_ids = fetch_game_ids(api_key)
    if game_ids:
        player_odds_df = fetch_nba_player_odds(api_key, game_ids)
        save_to_csv(player_odds_df)
        print(player_odds_df)

# Commenting out the function call to comply with the instructions
if __name__ == "__main__":
     main()
