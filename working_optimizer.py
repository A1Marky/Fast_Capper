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
import itertools

# Load environment variables
load_dotenv()
SABERSIM_API_KEY = os.getenv('SABERSIM_API_KEY')
ODDS_API_KEY = os.getenv('ODDS_API_KEY')
DEFAULT_EMAIL = os.getenv('SABERSIM_EMAIL')
DEFAULT_PASSWORD = os.getenv('SABERSIM_PASSWORD')

# Initialize a session to improve performance by reusing TCP connections
session = requests.Session()
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
                  "bookmakers": "espnbet"}
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

# Additional Functions from the second script
def load_data(file_path):
    return pd.read_csv(file_path)

def apply_filters(data, filters):
    for key, values in filters.items():
        if key in data.columns:
            if isinstance(values, list):
                data = data[data[key].isin(values)]
            elif isinstance(values, (int, float)):
                data = data[data[key] >= values]
            else:
                data = data[data[key] == values]
    return data

def calculate_parlay_edge(data, bet_type_to_stat):
    """
    Calculate the edge for each bet in the dataset for parlay optimization.
    """
    data['projected_stat'] = data['bet_type'].map(bet_type_to_stat)
    data['edge'] = data.apply(lambda row: row[row['projected_stat']] - row['stat_threshold']
                                        if row['over/under'] == 'Over'
                                        else row['stat_threshold'] - row[row['projected_stat']],
                              axis=1)
    return data.drop(columns=['projected_stat'])

def decimal_to_american(decimal_odds):
    """
    Convert decimal odds to American odds.
    """
    return int((decimal_odds - 1) * 100 if decimal_odds >= 2.0 else -100 / (decimal_odds - 1))

def calculate_position_strength(data):
    """
    Calculates each player's performance relative to their position average.
    """
    position_averages = data.groupby('position')[['points', 'assists', 'rebounds']].mean().add_suffix('_pos_avg')
    data = data.join(position_averages, on='position')
    for stat in ['points', 'assists', 'rebounds']:
        data[f'{stat}_diff'] = data[stat] - data[f'{stat}_pos_avg']
    return data

def get_best_stat(data):
    """
    Determine the best stat for each player.
    """
    stats_diff = data[['player_names', 'points_diff', 'assists_diff', 'rebounds_diff']]
    player_best_stat = stats_diff.groupby('player_names').mean()
    player_best_stat['best_stat'] = player_best_stat.idxmax(axis=1).str.replace('_diff', '')
    return player_best_stat

def optimize_parlay(data, num_legs, num_parlays, player_strengths):
    """
    Optimize parlay bets with the specified number of legs and parlays, ensuring uniqueness.
    """
    if 'odds' not in data.columns:
        raise ValueError("Data does not contain 'odds' column.")

    data['best_stat'] = data['player_names'].map(player_strengths['best_stat'])

    # Sort data by 'edge' in descending order to prioritize high edge bets
    data = data.sort_values(by='edge', ascending=False)

    # Remove bets with negative edge
    data = data[data['edge'] > 0]

    # Use all available bets indices for creating parlays
    all_bets_indices = data.index

    return create_parlay_combinations(data, all_bets_indices, num_parlays, num_legs)

def create_parlay_combinations(data, all_bets_indices, num_parlays, num_legs):
    """
    Create parlays with specified number of legs, ensuring each parlay is unique.
    """
    parlay_details = []
    used_bets = set()

    # Generate all possible combinations of bets
    all_combinations = list(itertools.combinations(all_bets_indices, num_legs))

    for combo in all_combinations:
        if len(parlay_details) >= num_parlays:
            break
        if not used_bets.intersection(set(combo)):
            combo_df = data.loc[list(combo)].copy()
            combo_df['us_odds'] = combo_df['odds'].apply(decimal_to_american)
            combined_odds = combo_df['odds'].product()
            american_combined_odds = decimal_to_american(combined_odds)
            parlay_details.append((combo_df, american_combined_odds))
            used_bets.update(combo)  # Add these bets to the used set

    return parlay_details

def combine_and_save_parlays(parlays):
    """
    Combines and saves parlay details.
    """
    combined_parlay_df = pd.DataFrame()
    for i, (parlay_df, total_odds) in enumerate(parlays):
        parlay_df['Parlay_Number'] = f"Parlay {i+1} (Edge Maximizing)"
        parlay_df['Total_Odds'] = total_odds
        combined_parlay_df = pd.concat([combined_parlay_df, parlay_df], ignore_index=True)
    return combined_parlay_df

def run_parlay_optimizer_app(file_path):
    """
    Streamlit app to run the parlay optimizer with the "Edge Maximizing" strategy.
    """
    st.title("Parlay Optimizer")

    # Load data directly from the given file path
    data = load_data(file_path)
    team_input = st.multiselect('Select Teams', options=data['team'].unique(), default=data['team'].unique())
    default_bet_types = ['player_points', 'player_points_alternate', 'player_assists', 'player_assists_alternate','player_rebounds', 'player_rebounds_alternate']
    bet_type_input = st.multiselect('Select Bet Types', options=data['bet_type'].unique(), default=default_bet_types)
    over_under_input = st.radio('Over/Under', ['Over', 'Under', 'Both'], index=0)
    min_minutes = st.slider('Minimum Minutes', 0, int(data['minutes'].max()), 28)

    filters = {
        'team': team_input,
        'bet_type': bet_type_input,
        'minutes': min_minutes
    }
    if over_under_input != 'Both':
        filters['over/under'] = over_under_input

    # Removed multiple strategy options, defaulting to "Edge Maximizing"
    strategy = "Edge Maximizing"

    num_legs = st.slider('Number of Legs', 1, 10, 3)
    num_parlays = st.slider('Number of Parlays', 1, 10, 5)

    if st.button('Calculate Parlays'):
        filtered_data = apply_filters(data, filters)
        bet_type_to_stat = {
            "player_points": "points",
            "player_points_alternate": "points",
            "player_rebounds": "rebounds",
            "player_rebounds_alternate": "rebounds",
            "player_assists": "assists",
            "player_assists_alternate": "assists"
        }
        data_with_edge = calculate_parlay_edge(filtered_data, bet_type_to_stat)
        data_with_position_strength = calculate_position_strength(data)
        player_strengths = get_best_stat(data_with_position_strength)
        
        available_bets_count = len(data_with_edge['player_names'].unique())
        
        if num_legs > available_bets_count:
            num_legs = available_bets_count
            st.warning(f"Adjusted number of legs to {num_legs} due to limited available bets.")

        parlays = optimize_parlay(data_with_edge, num_legs, num_parlays, player_strengths)
        if len(parlays) > 0:
            combined_parlays = combine_and_save_parlays(parlays)
            unique_parlay_numbers = combined_parlays['Parlay_Number'].unique()
            
            for parlay_number in unique_parlay_numbers:
                st.subheader(f"{parlay_number}")
                parlay_group = combined_parlays[combined_parlays['Parlay_Number'] == parlay_number]
                # Sort the parlay group by 'edge' in descending order
                parlay_group_sorted = parlay_group.sort_values(by='edge', ascending=False)
                st.write(parlay_group_sorted[['player_names', 'bet_type', 'over/under', 'stat_threshold', 'odds', 'us_odds', 'edge', 
                                                'position', 'team', 'opp', 'minutes', 'possessions', 'points', 'assists', 'rebounds', 'Total_Odds']])
        else:
            st.error("Not enough bets available to form a parlay with the specified criteria.")

# Main function
def main():
    # Set Streamlit page configuration to wide mode
    st.set_page_config(layout="wide")
    
    # Initialize session state variables
    if 'data_fetched' not in st.session_state:
        st.session_state['data_fetched'] = False
    if 'master_df_path' not in st.session_state:
        st.session_state['master_df_path'] = ''

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
                st.session_state['data_fetched'] = True
                st.session_state['master_df_path'] = 'master_df.csv'

                # UNCOMMENT THE CODE BELOW IF YOU WANT THE DATAFRAMES DISPLAYED ONTO THE STREAMLIT APP
                # st.write("Games Data:", games_df)
                # st.write("Master Dataframe:", master_df)
                
            except Exception as e:
                st.error(f"An error occurred: {e}")
        else:
            st.error("Authentication failed.")

    # Only run the parlay optimizer if the data has been fetched
    if st.session_state['data_fetched']:
        run_parlay_optimizer_app(st.session_state['master_df_path'])

if __name__ == "__main__":
    main()

