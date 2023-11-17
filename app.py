from odds import fetch_nba_game_ids, fetch_nba_player_odds, merge_sabersim_and_odds_data
import streamlit as st
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import seaborn as sns
import matplotlib.colors as mcolors


# Importing from api_functions
from api_functions import get_auth_token, get_slates, get_player_projections

# Set Streamlit page configuration to wide mode
st.set_page_config(layout="wide")

# Load environment variables
load_dotenv()

# Environment variables for email and password
SABERSIM_EMAIL = os.getenv('SABERSIM_EMAIL')
SABERSIM_PASSWORD = os.getenv('SABERSIM_PASSWORD')

# Automatically get auth token on app load
try:
    auth_token = get_auth_token(SABERSIM_EMAIL, SABERSIM_PASSWORD)
except Exception as e:
    st.error(f"Login failed: {e}")
    st.stop()

# Slates and Game Schedule section
st.sidebar.header("NBA Slates and Game Schedule")
# Using date_input for calendar selection. Default is set to today's date.
date = st.sidebar.date_input("Select a date", datetime.today())

# Toggle for multiple matchup filtering
enable_multi_filter = st.sidebar.checkbox("Enable Multiple Matchup Filtering")

# Function to create statistical leaderboards for all categories
def create_leaderboards(df, categories, top_n=10):
    leaderboards = {}
    for category in categories:
        sorted_df = df.sort_values(by=category, ascending=False).head(top_n)
        leaderboards[category] = sorted_df[['player_names', 'team', 'minutes', 'possessions', category]]
    return leaderboards


# Function to create a custom red-yellow-green color map
def create_custom_color_map():
    colors = ['red', 'yellow', 'green']  # Red for low, yellow for middle, green for high
    nodes = [0.0, 0.5, 1.0]
    cmap = mcolors.LinearSegmentedColormap.from_list("", list(zip(nodes, colors)))
    return cmap

# Function for applying conditional formatting with the custom red-yellow-green gradient and bold, readable text to DataFrame
def apply_gradient_formatting(df, column):
    cmap = create_custom_color_map()
    min_val = df[column].min()
    max_val = df[column].max()
    norm = mcolors.Normalize(min_val, max_val)
    colors = [mcolors.to_hex(cmap(norm(value))) for value in df[column]]

    def color_font(x):
        if x.name != column:
            return [''] * len(x)
        else:
            return [f'color: {"white" if cmap(norm(val))[0] < 0.5 else "black"}; font-weight: bold; background-color: {color}' 
                    for val, color in zip(x, colors)]

    return df.style.apply(color_font)


if date:
    try:
        # Format the date to YYYY-MM-DD for the API call
        formatted_date = date.strftime("%Y-%m-%d")

        # Automatically call get_slates when a date is entered
        slate_ids = get_slates(auth_token, formatted_date)
        
        # Automatically call get_player_projections after obtaining slate IDs
        player_projections_df = get_player_projections(auth_token, formatted_date, slate_ids)

      
        # Group by 'gid' and get the first 'matchup' for each group
        unique_matchups = player_projections_df.groupby('gid')['matchup'].first()

        # Sidebar for matchup selection
        if enable_multi_filter:
            selected_matchup_gids = st.sidebar.multiselect('Filter by Matchups', unique_matchups.index, format_func=lambda x: unique_matchups[x])
            filtered_df = player_projections_df[player_projections_df['gid'].isin(selected_matchup_gids)]
        else:
            selected_matchup_gid = st.sidebar.selectbox('Filter by Matchup', unique_matchups.index, format_func=lambda x: unique_matchups[x])
            filtered_df = player_projections_df[player_projections_df['gid'] == selected_matchup_gid]

        # Slider for filtering by minutes
        min_minutes, max_minutes = st.sidebar.slider(
            'Filter by Minutes', 
            float(player_projections_df['minutes'].min()), 
            float(player_projections_df['minutes'].max()), 
            (float(player_projections_df['minutes'].min()), float(player_projections_df['minutes'].max()))
        )
        filtered_df = filtered_df[(filtered_df['minutes'] >= min_minutes) & (filtered_df['minutes'] <= max_minutes)]

        # Section for Updating Odds
        st.sidebar.header("Odds Management")
        if st.sidebar.button("Update Odds"):
            try:
                # Fetch NBA game IDs
                game_ids = fetch_nba_game_ids()
                if game_ids:
                    # Fetch NBA player prop odds
                    player_odds_df = fetch_nba_player_odds(game_ids)
                    # Assuming filtered_df is already defined in the app
                    # Merge the odds data with the SaberSim projections
                    merged_df = merge_sabersim_and_odds_data(filtered_df, player_odds_df)
                    st.success("Odds updated successfully!")
                else:
                    st.warning("No game IDs fetched. Please check the API or network connection.")
            except Exception as e:
                st.error(f"Failed to update odds: {e}")


        # Leaderboard Section
        st.header("Projection Leaderboards")
        categories = ['points', 'assists', 'rebounds']
        leaderboards = create_leaderboards(filtered_df, categories)

        # Creating columns for side by side layout
        cols = st.columns(len(categories))
        for i, (category, df) in enumerate(leaderboards.items()):
            with cols[i]:
                st.subheader(f"Top 10 in {category.capitalize()}")
                formatted_df = apply_gradient_formatting(df, category)
                st.dataframe(formatted_df, hide_index=True)

        columns_to_display = [
            'player_names', 'position', 'team', 'opp', 'minutes', 'possessions','points', 'assists', 'rebounds', 
            'blocks', 'steals', 'fouls', 'turnovers','two_pt_attempts', 'two_pt_fg', 'three_pt_attempts', 'three_pt_fg', 
            'free_throw_attempts', 'free_throws_made', 'roster_pos', 'confirmed', 'double_doubles','triple_doubles', 
            'matchup'
        ]
        displayed_dataframe = filtered_df[columns_to_display]
        # Change the below line back for testing purposes only just uncomment it when needed
        #filtered_df.to_csv('optimizer_data.csv', index=False)
    
    except Exception as e:
        st.error(f"Failed to retrieve data: {e}")
