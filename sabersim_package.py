import requests
import pandas as pd
from datetime import datetime

# API Endpoints
AUTH_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={}"
SLATE_URL = "https://basketball-sim.appspot.com/_ah/api/nba/v1/slates"
PLAYER_PROJECTIONS_URL = "https://basketball-sim.appspot.com/endpoints/get_player_projections"
GAMES_SCHEDULE_URL = "https://basketball-sim.appspot.com/_ah/api/nba/v1/games"

def authenticate_user(email, password, api_key):
    """
    Authenticate user and retrieve authentication token.
    
    :param email: User's email
    :param password: User's password
    :param api_key: API key for the service
    :return: Authentication token
    """
    response = requests.post(AUTH_URL.format(api_key), json={
        "email": email, "password": password, "returnSecureToken": True, "clientType": "CLIENT_TYPE_WEB"
    }, headers={"Content-Type": "application/json"})
    
    # Raise an exception for HTTP error responses
    response.raise_for_status()
    return f"Bearer {response.json()['idToken']}"

def fetch_slates(date, sport, auth_token):
    """
    Fetch slates data for a given date and sport.
    
    :param date: Target date for the slates
    :param sport: Sport type (e.g., 'nba')
    :param auth_token: Authentication token
    :return: List of slate IDs
    """
    response = requests.get(f"{SLATE_URL}?date={date}&sport={sport}", headers={
        "Authorization": auth_token, "Accept": "application/json"
    })
    
    # Check for HTTP errors
    response.raise_for_status()
    # Filter for 'fd' site slates and return their IDs
    return [slate['id'] for slate in response.json()['slates'] if slate['site'] == 'fd']

def fetch_games_schedule(date, sport, slates, auth_token):
    """
    Fetch games schedule data for each slate ID, ensuring unique 'gid' values.
    
    :param date: Date for the games
    :param sport: Sport type
    :param slates: List of slate IDs
    :param auth_token: Authentication token
    :return: DataFrame of unique games
    """
    all_games = []
    for slate_id in slates:
        response = requests.get(f"{GAMES_SCHEDULE_URL}?date={date}&sport={sport}&slate={slate_id}", headers={
            "Authorization": auth_token, "Accept": "application/json"
        })
        
        # Validate response
        response.raise_for_status()
        games = response.json().get('games', [])
        all_games.extend(games)

    games_df = pd.DataFrame(all_games)
    # Ensure only unique games are included based on 'gid'
    unique_games_df = games_df.drop_duplicates(subset=['gid'], keep='first')
    # Select relevant columns
    columns_to_keep = ['away_score', 'away_team', 'away_wins', 'home_score', 'home_team', 'home_wins', 'start_time_js', 'gid']
    unique_games_df = unique_games_df[columns_to_keep]

    # Save the games schedule to a CSV for review
    unique_games_df.to_csv(f"games_schedule_{date}.csv", index=False)
    return unique_games_df

def fetch_player_projections(date, site, slates, sport, auth_token):
    """
    Fetch player projections for given slates, filtering for specified columns.
    
    :param date: Date for the projections
    :param site: Site code (e.g., 'fd' for FanDuel)
    :param slates: List of slate IDs
    :param sport: Sport type
    :param auth_token: Authentication token
    :return: DataFrame of player projections with specified columns
    """
    all_projections = []
    for slate_id in slates:
        response = requests.post(PLAYER_PROJECTIONS_URL, json={
            "date": date, "site": site, "slate": slate_id, "sport": sport
        }, headers={"Authorization": auth_token, "Content-Type": "application/json"})
        
        # Validate response
        response.raise_for_status()
        projections = response.json().get('players', [])
        all_projections.extend(projections)

    projections_df = pd.DataFrame(all_projections)
    # Rename columns for clarity
    projections_df.rename(columns={
        'name': 'player_names', 'fd_points': 'fanduel_fantasy_points', 'fd_std': 'fanduel_fantasy_points_standard_deviation'
    }, inplace=True)
    
    # Filter for specified columns only
    desired_columns = [
        'player_names', 'position', 'team', 'opp', 'minutes', 'possessions', 'fanduel_fantasy_points', 'points', 
        'assists', 'rebounds', 'offensive_rebounds', 'defensive_rebounds', 'blocks', 'steals', 'fouls', 'turnovers', 
        'two_pt_attempts', 'two_pt_fg', 'three_pt_attempts', 'three_pt_fg', 'free_throw_attempts', 'free_throws_made', 
        'roster_pos', 'confirmed', 'double_doubles', 'triple_doubles', 'injury', 'site', 
        'fanduel_fantasy_points_standard_deviation', 'timestamp', 'date', 'gid'
    ]
    
    return projections_df[desired_columns]

def main(date):
    """
    Main function to orchestrate fetching of slates, games schedule, and player projections.
    
    :param date: Date for fetching data
    """
    api_key = "AIzaSyB-UBUIJ9I76bTTFbriypJGR__FW-c47FM"
    user_email = "randywalker24@dispostable.com"
    user_password = "password123"
    sport = "nba"
    
    try:
        # Authenticate and get token
        auth_token = authenticate_user(user_email, user_password, api_key)
        # Fetch slates for the given date and sport
        slate_ids = fetch_slates(date, sport, auth_token)
        # Fetch and save games schedule and player projections if slates are available
        if slate_ids:
            games_schedule_df = fetch_games_schedule(date, sport, slate_ids, auth_token)
            projections_df = fetch_player_projections(date, "fd", slate_ids, sport, auth_token)
            projections_df.to_csv(f'player_projections_{date}.csv', index=False)
            print("Games Schedule:\n", games_schedule_df)
            print("Player Projections:\n", projections_df)
        else:
            print("No FD slates found for the specified criteria.")
    except requests.HTTPError as error:
        print(f"An HTTP error occurred: {error}")

if __name__ == "__main__":
    # Allows user to input a date or defaults to current date if none is provided
    date = input("Enter a date (YYYY-MM-DD): ") or datetime.now().strftime("%Y-%m-%d")
    main(date)
