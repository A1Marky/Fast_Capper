import pandas as pd
import itertools
import streamlit as st

def load_data(file_path):
    return pd.read_csv(file_path)

def calculate_edge(data, filters=None):
    """
    Calculate the edge for each bet in the dataset based on the projected stats and stat_threshold.
    
    :param data: DataFrame containing the betting data.
    :param filters: Dictionary containing user-specified filters (e.g., team, matchup, bet_type).
    :return: DataFrame with an additional 'edge' column.
    """
    if filters:
        # Apply filters to the data
        for key, values in filters.items():
            if key in data.columns:
                if isinstance(values, list):
                    # Filter for any of the values in the list
                    data = data[data[key].isin(values)]
                elif isinstance(values, (int, float)):
                    # Filter for a numerical condition (greater than or equal)
                    data = data[data[key] >= values]
                else:
                    # Filter for a single value
                    data = data[data[key] == values]

    # Define the relevant stat column based on bet_type
    bet_type_to_stat = {
        "player_points": "points",
        "player_rebounds": "rebounds",
        "player_assists": "assists",
        # Add other bet types and corresponding stat columns as needed
    }

    # Filter data to include only the bet types that are mapped and create a copy
    data = data[data['bet_type'].isin(bet_type_to_stat.keys())].copy()

    # Calculate the edge
    edges = []
    for index, row in data.iterrows():
        bet_type = row['bet_type']
        over_under = row['over/under']
        stat_threshold = row['stat_threshold']
        projected_stat = row[bet_type_to_stat[bet_type]] if bet_type in bet_type_to_stat else 0

        # Calculate edge based on over/under
        if over_under == 'Over':
            edge = projected_stat - stat_threshold
        else:  # 'Under'
            edge = stat_threshold - projected_stat

        edges.append(edge)

    # Add the edge column to the DataFrame
    data.loc[:, 'edge'] = edges
    return data

def decimal_to_american(decimal_odds):
    if decimal_odds >= 2.0:
        american_odds = (decimal_odds - 1) * 100
    else:
        american_odds = -100 / (decimal_odds - 1)
    return int(american_odds)

def optimize_parlay(data, num_legs, num_parlays, strategy):
    # Ensure 'odds' column exists
    if 'odds' not in data.columns:
        raise ValueError("Data does not contain 'odds' column.")

    # Make a copy of the data to avoid SettingWithCopyWarning
    data = data.copy()

    # Filter out bets with a negative edge for Conservative and Balanced strategies
    if strategy != "High-Risk, High-Reward":
        data = data[data['edge'] > 0]

    # Sort bets based on the strategy
    if strategy == "High-Risk, High-Reward":
        sorted_bets = data.sort_values(by='odds', ascending=False)
    elif strategy == "Balanced":
        data['balanced_score'] = data['edge'] * data['odds']
        sorted_bets = data.sort_values(by='balanced_score', ascending=False)
    else:  # Conservative
        sorted_bets = data.sort_values(by='edge', ascending=True)

    # Initialize a set to track bets used in previous parlays
    used_bets = set()
    parlay_details = []

    # Iterate to create each parlay
    for _ in range(num_parlays):
        top_indices = sorted_bets.index.difference(used_bets).tolist()
        top_combinations = itertools.combinations(top_indices[:num_legs * 10], num_legs)

        for combination_indices in top_combinations:
            if not set(combination_indices).intersection(used_bets):
                combo_df = data.loc[list(combination_indices)].copy()
                combo_df['us_odds'] = combo_df['odds'].apply(decimal_to_american)
                combined_odds = combo_df['odds'].product()
                american_combined_odds = decimal_to_american(combined_odds)
                parlay_details.append((combo_df, american_combined_odds))
                used_bets.update(combination_indices)
                break

    return parlay_details[:num_parlays]

def combine_and_save_parlays(parlays, strategy):
    combined_parlay_df = pd.DataFrame()
    for i, (parlay_df, total_odds) in enumerate(parlays):
        parlay_df['Parlay_Number'] = f"Parlay {i+1} ({strategy})"
        parlay_df['Total_Odds'] = total_odds
        combined_parlay_df = pd.concat([combined_parlay_df, parlay_df], ignore_index=True)
    return combined_parlay_df

def run_parlay_optimizer_app():
    st.title("Parlay Optimizer")

    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    if uploaded_file is not None:
        data = load_data(uploaded_file)

        team_input = st.multiselect('Select Teams', options=data['team'].unique(), default=data['team'].unique())
        default_bet_types = ['player_points', 'player_assists', 'player_rebounds']
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

        strategy = st.selectbox('Choose Your Strategy', ('High-Risk, High-Reward', 'Balanced', 'Conservative'))

        num_legs = st.slider('Number of Legs', 1, 10, 3)
        num_parlays = st.slider('Number of Parlays', 1, 10, 5)

        if st.button('Calculate Parlays'):
            data_with_edge = calculate_edge(data, filters=filters)
            parlays = optimize_parlay(data_with_edge, num_legs, num_parlays, strategy)
            combined_parlays = combine_and_save_parlays(parlays, strategy)

            unique_parlay_numbers = combined_parlays['Parlay_Number'].unique()
            for parlay_number in unique_parlay_numbers:
                st.subheader(f"{parlay_number}")
                parlay_group = combined_parlays[combined_parlays['Parlay_Number'] == parlay_number]
                st.write(parlay_group[['player_names', 'bet_type', 'over/under', 'stat_threshold', 'odds', 'us_odds', 'edge', 
                                       'position', 'team', 'opp', 'minutes', 'possessions', 'points', 'assists', 'rebounds', 'Total_Odds']])

if __name__ == "__main__":
    run_parlay_optimizer_app()
