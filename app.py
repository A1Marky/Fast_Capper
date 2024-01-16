import streamlit as st
from datetime import datetime
import nba_projections
import nba_odds
import pandas as pd

# Streamlit UI Components
st.title("NBA Player Projections App")

# User inputs
email = st.sidebar.text_input("Email", "zaclayne24@dispostable.com")
password = st.sidebar.text_input("Password", "password123", type="password")
date = st.sidebar.date_input("Date", datetime.today())

def identify_best_bets(df, stat_column, bet_type_prefix):
    best_bets = []
    for _, row in df.iterrows():
        if bet_type_prefix in row['bet_type']:
            stat_projection = row[stat_column]
            stat_threshold = row['stat_threshold']
            
            # Calculate the edge
            edge = abs(stat_projection - stat_threshold)

            if 'Over' in row['over/under'] and stat_projection > stat_threshold:
                row['edge'] = edge  # Positive edge for favorable over bets
                best_bets.append(row)
            elif 'Under' in row['over/under'] and stat_projection < stat_threshold:
                row['edge'] = edge  # Positive edge for favorable under bets
                best_bets.append(row)
    
    return pd.DataFrame(best_bets)

if st.sidebar.button("Fetch Projections and Update Odds"):
    try:
        # Fetch Projections
        auth_token = nba_projections.get_auth_token(email, password)
        slate_ids = nba_projections.get_slates(auth_token, date.strftime("%Y-%m-%d"))
        if slate_ids:
            player_projections_df = nba_projections.get_player_projections(auth_token, date.strftime("%Y-%m-%d"), slate_ids)
            st.write("Player projections fetched successfully.")
        else:
            st.warning("No slates available for the given date.")

        # Update Odds
        game_ids = nba_odds.fetch_nba_game_ids()
        if game_ids:
            odds_df = nba_odds.fetch_nba_player_odds(game_ids)
            st.write("Odds updated successfully.")
        else:
            st.warning("No NBA game IDs found.")

        # Merge DataFrames
        merged_df = pd.merge(player_projections_df, odds_df, on='player_names', how='left')
        merged_df.to_csv('merged_dataframes.csv', index=False)
        st.dataframe(merged_df)  # Displaying the merged DataFrame

        # Identify Best Bets
        betting_df = merged_df.dropna(subset=['bet_type', 'over/under', 'odds', 'stat_threshold'])
        best_bets_points = identify_best_bets(betting_df, 'points', 'player_points')
        best_bets_alt_points = identify_best_bets(betting_df, 'points', 'player_points_alternate')
        best_bets_assists = identify_best_bets(betting_df, 'assists', 'player_assists')
        best_bets_alt_assists = identify_best_bets(betting_df, 'assists', 'player_assists_alternate')
        best_bets_rebounds = identify_best_bets(betting_df, 'rebounds', 'player_rebounds')
        best_bets_alt_rebounds = identify_best_bets(betting_df, 'rebounds', 'player_rebounds_alternate')
        
        # Combine best bets into one dataframe
        best_bets_combined = pd.concat([best_bets_points, best_bets_alt_points, best_bets_assists, best_bets_alt_assists, best_bets_rebounds, best_bets_alt_rebounds])
        # Display the best bets dataframe
        if not best_bets_combined.empty:
            st.write("Best bets identified:")
            st.dataframe(best_bets_combined)
        else:
            st.write("No best bets identified based on current data.")

    except Exception as e:
        st.error(f"Error in processing: {e}")