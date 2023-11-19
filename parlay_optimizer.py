import pandas as pd
import itertools

# Load the dataset
file_path = 'merged_data.csv'
data = pd.read_csv(file_path)

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

# Define your filters
filters = {
    'matchup': ['LAL vs HOU', 'PHI vs BKN', 'POR vs OKC', 'PHO vs UTA'],
    'bet_type': ['player_points', 'player_assists', 'player_rebounds'],
    'minutes': 45  # Minimum minutes
}

# Calculate edge and optimize parlays
# Apply the filters when calling calculate_edge
data_with_edge = calculate_edge(data, filters=filters)
parlays = optimize_parlay(data_with_edge, num_legs=3, num_parlays=4)

# Combining and saving the parlays to a CSV file
combined_parlay_df = pd.DataFrame()

for i, (parlay_df, _) in enumerate(parlays):
    parlay_df['Parlay_Number'] = f"Parlay {i+1}"
    combined_parlay_df = pd.concat([combined_parlay_df, parlay_df], ignore_index=True)

# Writing the combined DataFrame to a CSV file
output_file_path = "optimized_parlays.csv"
combined_parlay_df.to_csv(output_file_path, index=False)

print(f"Parlays have been saved to '{output_file_path}'.")


