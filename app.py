import streamlit as st
import os
from datetime import datetime
from dotenv import load_dotenv

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

        # Display the filtered dataframe
        st.dataframe(filtered_df, hide_index=True)
        filtered_df.to_csv('optimizer_data.csv', index=False)
    except Exception as e:
        st.error(f"Failed to retrieve data: {e}")
