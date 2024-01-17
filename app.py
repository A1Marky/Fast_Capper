import os
from dotenv import load_dotenv
import streamlit as st
import pandas as pd
from player_odds import fetch_nba_game_ids, fetch_nba_player_odds
from player_projections import get_auth_token, get_slates, get_player_projections, get_games_data  # Add get_games_data import

# Load environment variables
load_dotenv()

# Environment variables for email and password
SABERSIM_EMAIL = os.getenv('SABERSIM_EMAIL')
SABERSIM_PASSWORD = os.getenv('SABERSIM_PASSWORD')

# Define Email and Password Login authentication
email = SABERSIM_EMAIL
password = SABERSIM_PASSWORD

# Set Streamlit page configuration to wide mode
st.set_page_config(layout="wide")

# Initialize Streamlit app
st.title("NBA Odds and Projections App")

# Button to trigger data fetching and merging
if st.button("Fetch and Merge Data"):
    if email and password:
        try:
            # Get authentication token
            auth_token = get_auth_token(email, password)
            
            # Fetch NBA game IDs and player odds
            game_ids = fetch_nba_game_ids()
            odds_df = fetch_nba_player_odds(game_ids)

            # Fetch slates and player projections
            date = pd.to_datetime('today').strftime('%Y-%m-%d')  # Assuming fetching for today's date
            slates = get_slates(auth_token, date)
            projections_df = get_player_projections(auth_token, date, slates)

            # Fetch game data for each slate
            games_data = get_games_data(auth_token, date, slates)
            
            # Process games_data as needed here...
            games_df = pd.DataFrame(games_data)
            games_df.to_csv('games_df.csv', index=False)
            
            # Define columns to keep in the DataFrame
            games_df_columns_to_keep = [
                'away_score', 'away_team', 'away_wins', 'home_score', 'home_team', 'home_wins', 'start_time_js'
            ]
            # Display the Games DataFrame
            st.dataframe(games_df[games_df_columns_to_keep])
            
            # Merge DataFrames (odds_df with projections_df)
            # Optionally merge with games_data if needed
           
            merged_df = pd.merge(odds_df, projections_df, on='player_names', how='left')
            merged_df.to_csv('merged_dataframes.csv', index=False)

            # Define columns to keep in the DataFrame
            columns_to_keep = [
                'sports_book', 'team', 'position', 'player_names', 'bet_type', 'over/under', 'stat_threshold', 'odds',
                'us_odds', 'minutes', 'possessions', 'points', 'assists', 'rebounds', 'blocks', 'steals', 
                'three_pt_fg', 'three_pt_attempts', 'gid', 'matchup'
            ]

            # Display the merged DataFrame
            st.dataframe(merged_df[columns_to_keep])

        except Exception as e:
            st.error(f"An error occurred: {e}")
    else:
        st.error("Please enter email and password.")

# Streamlit app end
