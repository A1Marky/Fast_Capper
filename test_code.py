import pandas as pd
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
    Apply filters to the dataset based on user input.
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
    Optimize parlay bets with the "Edge Maximizing" strategy.
    """
    if 'odds' not in data.columns:
        raise ValueError("Data does not contain 'odds' column.")

    data['best_stat'] = data['player_names'].map(player_strengths['best_stat'])
    
    # Sort data by 'edge' in descending order to prioritize high edge bets
    data = data.sort_values(by='edge', ascending=False)

    # Remove bets with negative edge
    data = data[data['edge'] > 0]

    core_bets, variable_bets_indices = select_core_and_variable_bets(data, num_legs)

    return create_parlay_combinations(data, core_bets, variable_bets_indices, num_parlays)

def select_core_and_variable_bets(sorted_bets, num_legs):
    """
    Select core and variable bets for the parlays.
    """
    core_bets = sorted_bets.head(num_legs - 1)
    return core_bets, sorted_bets.drop(core_bets.index).index

def create_parlay_combinations(data, core_bets, variable_bets_indices, num_parlays):
    """
    Create combinations for the parlays.
    """
    parlay_details = []
    used_bets = set(core_bets.index.tolist())

    for index in variable_bets_indices:
        if len(parlay_details) >= num_parlays:
            break
        if index not in used_bets:
            parlay_indices = core_bets.index.tolist() + [index]
            combo_df = data.loc[parlay_indices].copy()
            combo_df['us_odds'] = combo_df['odds'].apply(decimal_to_american)
            combined_odds = combo_df['odds'].product()
            american_combined_odds = decimal_to_american(combined_odds)
            parlay_details.append((combo_df, american_combined_odds))
            used_bets.add(index)

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
    Maintains the state of the parlays across reruns using st.session_state.
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

        num_legs = st.slider('Number of Legs', 1, 10, 3)
        num_parlays = st.slider('Number of Parlays', 1, 10, 5)

        calculate_button = st.button('Calculate Parlays')
        if calculate_button or 'parlays' not in st.session_state:
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
                st.session_state.parlays = combined_parlays  # Store parlays in session_state
            else:
                st.error("Not enough bets available to form a parlay with the specified criteria.")

        if 'parlays' in st.session_state:
            for parlay_number in st.session_state.parlays['Parlay_Number'].unique():
                st.subheader(f"{parlay_number}")
                parlay_group = st.session_state.parlays[st.session_state.parlays['Parlay_Number'] == parlay_number]
                display_cols = ['player_names', 'bet_type', 'over/under', 'stat_threshold', 'odds', 'us_odds', 'edge', 
                                'position', 'team', 'opp', 'minutes', 'possessions', 'points', 'assists', 'rebounds', 'Total_Odds']
                st.write(parlay_group[display_cols])

                # Dropdown to select legs to remove
                legs_to_remove = st.multiselect(
                    f"Select legs to remove from {parlay_number}",
                    options=parlay_group.index.tolist(),
                    format_func=lambda x: f"{parlay_group.at[x, 'player_names']} - {parlay_group.at[x, 'bet_type']}",
                    key=f"remove_{parlay_number}"
                )

                # Button to recalculate odds
                recalculate_key = f'recalculate_{parlay_number}'
                if st.button('Recalculate Odds', key=recalculate_key):
                    remaining_legs = parlay_group.drop(legs_to_remove)
                    if not remaining_legs.empty:
                        new_combined_odds = remaining_legs['odds'].product()
                        new_american_odds = decimal_to_american(new_combined_odds)
                        
                        # Update the session state with the remaining legs and recalculated odds
                        st.session_state.parlays.loc[remaining_legs.index, 'Total_Odds'] = new_american_odds
                        
                        # Display the new total odds above the Recalculate button, specifying the parlay number
                        st.write(f"{parlay_number} - New Total Odds (American): {new_american_odds}")
                        
                        # Display the updated parlay group
                        st.write(remaining_legs[display_cols])
                    else:
                        st.write("No legs left in the parlay.")
                else:
                    # Display a message if there are no parlays to show
                    st.write("No parlays to display.")

if __name__ == "__main__":
    run_parlay_optimizer_app()
