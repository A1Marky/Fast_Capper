import streamlit as st
from api_functions import get_auth_token, get_slates, get_player_projections, get_game_schedule
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Environment variables for email and password
SABERSIM_EMAIL = os.getenv('SABERSIM_EMAIL')
SABERSIM_PASSWORD = os.getenv('SABERSIM_PASSWORD')

# Initialize the Streamlit app
st.title("NBA Player Prop Sports Betting App")

# Automatically get auth token on app load
try:
    auth_token = get_auth_token(SABERSIM_EMAIL, SABERSIM_PASSWORD)
    st.success("Logged in successfully!")
except Exception as e:
    st.error(f"Login failed: {e}")
    st.stop()

# Slates and Game Schedule section
st.header("NBA Slates and Game Schedule")
date = st.text_input("Enter date (YYYY-MM-DD)", "2023-11-06")

if date:
    try:
        # Automatically call get_slates when a date is entered
        slate_ids = get_slates(auth_token, date)
        
        # Automatically call get_player_projections after obtaining slate IDs
        player_projections_df = get_player_projections(auth_token, date, slate_ids)
        
        # Display the player projections DataFrame in the Streamlit app
        st.dataframe(player_projections_df, hide_index=True)

        # Fetch and display the game schedule using the first slate ID from get_slates
        game_schedule_df = get_game_schedule(auth_token, date)
        st.subheader("Game Schedule")
        st.dataframe(game_schedule_df, hide_index=True)

    except Exception as e:
        st.error(f"Failed to retrieve data: {e}")

# Themed Layout and Branding (This requires configuration in `.streamlit/config.toml`)
# Refer to Streamlit documentation for theme customization

# Ensure to test the app after integrating these changes for any adjustments or error handling.
