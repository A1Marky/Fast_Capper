import pandas as pd
import itertools
import streamlit as st

# Set Streamlit page configuration to wide mode
st.set_page_config(layout="wide")

def load_data(file_path):
    """
    Load data from a CSV file.
    """
    return pd.read_csv(file_path)

def apply_filters(data, filters):
    """
    Apply filters to the dataset.
    """
    for key, values in filters.items():
        if key in data.columns:
            if isinstance(values, list):
                data = data[data[key].isin(values)]
            elif isinstance(values, (int, float)):
                data = data[data[key] >= values]
            else:
                data = data[data[key] == values]
    return data

def calculate_edge(data, bet_type_to_stat):
    """
    Calculate the edge for each bet in the dataset.
    """
    data['projected_stat'] = data['bet_type'].map(bet_type_to_stat)
    data['edge'] = data.apply(lambda row: row[row['projected_stat']] - row['stat_threshold']
                                        if row['over/under'] == 'Over'
                                        else row['stat_threshold'] - row[row['projected_stat']],
                              axis=1)
    return data.drop(columns=['projected_stat'])

def decimal_to_american(decimal_odds):
    """
    Convert decimal odds to American odds.
    """
    return int((decimal_odds - 1) * 100 if decimal_odds >= 2.0 else -100 / (decimal_odds - 1))

def calculate_position_strength(data):
    """
    Calculates each player's performance relative to their position average.
    """
    position_averages = data.groupby('position')[['points', 'assists', 'rebounds']].mean().add_suffix('_pos_avg')
    data = data.join(position_averages, on='position')
    for stat in ['points', 'assists', 'rebounds']:
        data[f'{stat}_diff'] = data[stat] - data[f'{stat}_pos_avg']
    return data

def get_best_stat(data):
    """
    Determine the best stat for each player.
    """
    stats_diff = data[['player_names', 'points_diff', 'assists_diff', 'rebounds_diff']]
    player_best_stat = stats_diff.groupby('player_names').mean()
    player_best_stat['best_stat'] = player_best_stat.idxmax(axis=1).str.replace('_diff', '')
    return player_best_stat

def optimize_parlay(data, num_legs, num_parlays, player_strengths):
    """
    Optimize parlay bets with the specified number of legs and parlays, ensuring uniqueness.
    """
    if 'odds' not in data.columns:
        raise ValueError("Data does not contain 'odds' column.")

    data['best_stat'] = data['player_names'].map(player_strengths['best_stat'])

    # Sort data by 'edge' in descending order to prioritize high edge bets
    data = data.sort_values(by='edge', ascending=False)

    # Remove bets with negative edge
    data = data[data['edge'] > 0]

    # Use all available bets indices for creating parlays
    all_bets_indices = data.index

    return create_parlay_combinations(data, all_bets_indices, num_parlays, num_legs)

def create_parlay_combinations(data, all_bets_indices, num_parlays, num_legs):
    """
    Create parlays with specified number of legs, ensuring each parlay is unique.
    """
    parlay_details = []
    used_bets = set()

    # Generate all possible combinations of bets
    all_combinations = list(itertools.combinations(all_bets_indices, num_legs))

    for combo in all_combinations:
        if len(parlay_details) >= num_parlays:
            break
        if not used_bets.intersection(set(combo)):
            combo_df = data.loc[list(combo)].copy()
            combo_df['us_odds'] = combo_df['odds'].apply(decimal_to_american)
            combined_odds = combo_df['odds'].product()
            american_combined_odds = decimal_to_american(combined_odds)
            parlay_details.append((combo_df, american_combined_odds))
            used_bets.update(combo)  # Add these bets to the used set

    return parlay_details





def combine_and_save_parlays(parlays):
    """
    Combines and saves parlay details.
    """
    combined_parlay_df = pd.DataFrame()
    for i, (parlay_df, total_odds) in enumerate(parlays):
        parlay_df['Parlay_Number'] = f"Parlay {i+1} (Edge Maximizing)"
        parlay_df['Total_Odds'] = total_odds
        combined_parlay_df = pd.concat([combined_parlay_df, parlay_df], ignore_index=True)
    return combined_parlay_df

def run_parlay_optimizer_app():
    """
    Streamlit app to run the parlay optimizer with the "Edge Maximizing" strategy.
    """
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

        # Removed multiple strategy options, defaulting to "Edge Maximizing"
        strategy = "Edge Maximizing"

        num_legs = st.slider('Number of Legs', 1, 10, 3)
        num_parlays = st.slider('Number of Parlays', 1, 10, 5)

        if st.button('Calculate Parlays'):
            filtered_data = apply_filters(data, filters)
            bet_type_to_stat = {
                "player_points": "points",
                "player_rebounds": "rebounds",
                "player_assists": "assists"
            }
            data_with_edge = calculate_edge(filtered_data, bet_type_to_stat)
            data_with_position_strength = calculate_position_strength(data)
            player_strengths = get_best_stat(data_with_position_strength)
            
            available_bets_count = len(data_with_edge['player_names'].unique())
            
            if num_legs > available_bets_count:
                num_legs = available_bets_count
                st.warning(f"Adjusted number of legs to {num_legs} due to limited available bets.")

            parlays = optimize_parlay(data_with_edge, num_legs, num_parlays, player_strengths)
            if len(parlays) > 0:
                combined_parlays = combine_and_save_parlays(parlays)
                unique_parlay_numbers = combined_parlays['Parlay_Number'].unique()
                
                for parlay_number in unique_parlay_numbers:
                    st.subheader(f"{parlay_number}")
                    parlay_group = combined_parlays[combined_parlays['Parlay_Number'] == parlay_number]
                    # Sort the parlay group by 'edge' in descending order
                    parlay_group_sorted = parlay_group.sort_values(by='edge', ascending=False)
                    st.write(parlay_group_sorted[['player_names', 'bet_type', 'over/under', 'stat_threshold', 'odds', 'us_odds', 'edge', 
                                                  'position', 'team', 'opp', 'minutes', 'possessions', 'points', 'assists', 'rebounds', 'Total_Odds']])
            else:
                st.error("Not enough bets available to form a parlay with the specified criteria.")

if __name__ == "__main__":
    run_parlay_optimizer_app()
