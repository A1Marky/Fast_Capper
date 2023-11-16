import streamlit as st
from api_functions import get_auth_token, get_slates, get_player_projections
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Environment variables for email and password
SABERSIM_EMAIL = os.getenv('SABERSIM_EMAIL')
SABERSIM_PASSWORD = os.getenv('SABERSIM_PASSWORD')

# Initialize the Streamlit app
st.title("NBA Player Prop Sports Betting App")

# Automatically get auth token on app load.
try:
    auth_token = get_auth_token(SABERSIM_EMAIL, SABERSIM_PASSWORD)
    st.success("Logged in successfully!")
except Exception as e:
    st.error(f"Login failed: {e}")
    st.stop()

# Slates section
st.header("NBA Slates")
date = st.text_input("Enter date (YYYY-MM-DD)", "2023-11-06")

if date:
    try:
        # Automatically call get_slates when a date is entered
        slate_ids = get_slates(auth_token, date)
        
        # Automatically call get_player_projections after obtaining slate IDs
        player_projections_df = get_player_projections(auth_token, date, slate_ids)
        
        # Display the DataFrame in the Streamlit app
        st.dataframe(player_projections_df)
        
    except Exception as e:
        st.error(f"Failed to get player projections: {e}")
