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

def optimize_parlay(data, num_legs, num_parlays):
    """
    Optimize and return a specified number of parlay bet combinations.
    
    :param data: DataFrame containing the betting data with edge calculations.
    :param num_legs: Number of legs in each parlay bet.
    :param num_parlays: Number of parlay combinations to return.
    :return: List of DataFrames, each containing an optimized combination of bets.
    """
    # Ensure 'odds' column exists
    if 'odds' not in data.columns:
        raise ValueError("Data does not contain 'odds' column.")

    # Filter out bets with a negative edge
    positive_edge_bets = data[data['edge'] > 0].copy()

    # Create a 'score' column to sort bets
    positive_edge_bets.loc[:, 'score'] = positive_edge_bets['edge'] * positive_edge_bets['odds']
    sorted_bets = positive_edge_bets.sort_values(by='score', ascending=False)

    # Generate combinations using indices of the sorted bets
    top_indices = sorted_bets.head(num_legs * 10).index
    top_combinations = itertools.combinations(top_indices, num_legs)

    # Evaluate each combination and store its details
    parlay_details = []
    for combination_indices in top_combinations:
        combo_df = data.loc[list(combination_indices)]

        combined_odds = combo_df['odds'].product()
        parlay_details.append((combo_df, combined_odds))

    # Sort the combinations by combined odds
    parlay_details.sort(key=lambda x: x[1], reverse=True)

    # Return the top specified number of parlays
    return parlay_details[:num_parlays]

def combine_and_save_parlays(parlays):
    combined_parlay_df = pd.DataFrame()
    for i, (parlay_df, _) in enumerate(parlays):
        parlay_df['Parlay_Number'] = f"Parlay {i+1}"
        combined_parlay_df = pd.concat([combined_parlay_df, parlay_df], ignore_index=True)
    return combined_parlay_df

# Streamlit app function
def run_parlay_optimizer_app():
    st.title("Parlay Optimizer")

    # File uploader
    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    if uploaded_file is not None:
        data = load_data(uploaded_file)

        # User inputs for filters
        team_input = st.multiselect('Select Teams', options=data['team'].unique(), default=data['team'].unique())
        default_bet_types = ['player_points', 'player_assists', 'player_rebounds']
        bet_type_input = st.multiselect('Select Bet Types', options=data['bet_type'].unique(), default=default_bet_types)
        min_minutes = st.slider('Minimum Minutes', 0, int(data['minutes'].max()), 28)

        filters = {
            'team': team_input,
            'bet_type': bet_type_input,
            'minutes': min_minutes
        }

        # User inputs for parlay configuration
        num_legs = st.slider('Number of Legs', 1, 10, 3)
        num_parlays = st.slider('Number of Parlays', 1, 10, 5)

        if st.button('Calculate Parlays'):
            # Apply filters and calculate
            data_with_edge = calculate_edge(data, filters=filters)
            parlays = optimize_parlay(data_with_edge, num_legs, num_parlays)
            combined_parlays = combine_and_save_parlays(parlays)

            # Display results with specified columns
            columns_to_display = ['Parlay_Number','player_names', 'bet_type', 'over/under', 'stat_threshold', 'odds', 'edge', 
                                  'position', 'team', 'opp', 'minutes', 'possessions', 'points', 'assists', 'rebounds']
            st.write(combined_parlays[columns_to_display],)

# Run the app
if __name__ == "__main__":
    run_parlay_optimizer_app()
