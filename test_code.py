import pandas as pd
import itertools
import streamlit as st

def load_data(file_path):
    """
    Load data from a CSV file.
    """
    return pd.read_csv(file_path)

def calculate_edge(data, filters=None):
    """
    Calculate the edge for each bet in the dataset based on the projected stats and stat_threshold.
    """
    if filters:
        for key, values in filters.items():
            if key in data.columns:
                if isinstance(values, list):
                    data = data[data[key].isin(values)]
                elif isinstance(values, (int, float)):
                    data = data[data[key] >= values]
                else:
                    data = data[data[key] == values]

    bet_type_to_stat = {
        "player_points": "points",
        "player_rebounds": "rebounds",
        "player_assists": "assists",
        # Add other bet types and corresponding stat columns as needed
    }

    data = data[data['bet_type'].isin(bet_type_to_stat.keys())].copy()

    edges = []
    for index, row in data.iterrows():
        bet_type = row['bet_type']
        over_under = row['over/under']
        stat_threshold = row['stat_threshold']
        projected_stat = row[bet_type_to_stat[bet_type]] if bet_type in bet_type_to_stat else 0

        if over_under == 'Over':
            edge = projected_stat - stat_threshold
        else:
            edge = stat_threshold - projected_stat

        edges.append(edge)

    data.loc[:, 'edge'] = edges
    return data

def decimal_to_american(decimal_odds):
    """
    Convert decimal odds to American odds.
    """
    if decimal_odds >= 2.0:
        american_odds = (decimal_odds - 1) * 100
    else:
        american_odds = -100 / (decimal_odds - 1)
    return int(american_odds)

def player_stat_strength_position_based(data):
    """
    Calculates each player's performance relative to the average performance of their position.
    """
    position_averages = data.groupby('position')[['points', 'assists', 'rebounds']].mean()
    data_with_position_avg = data.join(position_averages, on='position', rsuffix='_pos_avg')
    for stat in ['points', 'assists', 'rebounds']:
        data_with_position_avg[f'{stat}_diff'] = data_with_position_avg[stat] - data_with_position_avg[f'{stat}_pos_avg']
    player_best_stat = data_with_position_avg.groupby('player_names')[['points_diff', 'assists_diff', 'rebounds_diff']].mean()
    player_best_stat['best_stat'] = player_best_stat.idxmax(axis=1).str.replace('_diff', '')
    return player_best_stat

def optimize_parlay(data, num_legs, num_parlays, strategy, player_strengths):
    if 'odds' not in data.columns:
        raise ValueError("Data does not contain 'odds' column.")
    data = data.copy()
    data = data.join(player_strengths['best_stat'], on='player_names')

    # Sort and filter data based on the selected strategy
    if strategy != "High-Risk, High-Reward":
        data = data[data['edge'] > 0]
    if strategy == "High-Risk, High-Reward":
        sorted_bets = data.sort_values(by='odds', ascending=False)
    elif strategy == "Balanced":
        data['balanced_score'] = data['edge'] * data['odds']
        sorted_bets = data.sort_values(by='balanced_score', ascending=False)
    else:  # Conservative
        sorted_bets = data.sort_values(by='edge', ascending=True)

    # Identifying the core bets (num_legs - 1 strongest bets)
    core_bets = sorted_bets.head(num_legs - 1)
    variable_bets_indices = sorted_bets.drop(core_bets.index).index

    parlay_details = []
    used_bets = set(core_bets.index.tolist())

    # Creating parlays with varied legs using only the indices of variable bets
    for index in variable_bets_indices:
        if len(parlay_details) >= num_parlays:
            break  # Limit the number of parlays generated

        if index not in used_bets:
            parlay_indices = core_bets.index.tolist() + [index]
            combo_df = data.loc[parlay_indices].copy()
            combo_df['us_odds'] = combo_df['odds'].apply(decimal_to_american)
            combined_odds = combo_df['odds'].product()
            american_combined_odds = decimal_to_american(combined_odds)
            parlay_details.append((combo_df, american_combined_odds))
            used_bets.add(index)

    return parlay_details

def combine_and_save_parlays(parlays, strategy):
    """
    Combines and saves parlay details.
    """
    combined_parlay_df = pd.DataFrame()
    for i, (parlay_df, total_odds) in enumerate(parlays):
        parlay_df['Parlay_Number'] = f"Parlay {i+1} ({strategy})"
        parlay_df['Total_Odds'] = total_odds
        combined_parlay_df = pd.concat([combined_parlay_df, parlay_df], ignore_index=True)
    return combined_parlay_df

def run_parlay_optimizer_app():
    """
    Streamlit app to run the parlay optimizer.
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

        strategy = st.selectbox('Choose Your Strategy', ('High-Risk, High-Reward', 'Balanced', 'Conservative'))

        num_legs = st.slider('Number of Legs', 1, 10, 3)
        num_parlays = st.slider('Number of Parlays', 1, 10, 5)

        if st.button('Calculate Parlays'):
            data_with_edge = calculate_edge(data, filters=filters)
            player_strengths = player_stat_strength_position_based(data)
            
            # Check the number of unique bets available after filters
            available_bets_count = len(data_with_edge['player_names'].unique())
            
            # Adjust the number of legs if necessary
            if num_legs > available_bets_count:
                num_legs = available_bets_count
                st.warning(f"Adjusted number of legs to {num_legs} due to limited available bets.")

            parlays = optimize_parlay(data_with_edge, num_legs, num_parlays, strategy, player_strengths)
            if len(parlays) > 0:
                combined_parlays = combine_and_save_parlays(parlays, strategy)
                unique_parlay_numbers = combined_parlays['Parlay_Number'].unique()
                
                for parlay_number in unique_parlay_numbers:
                    st.subheader(f"{parlay_number}")
                    parlay_group = combined_parlays[combined_parlays['Parlay_Number'] == parlay_number]
                    st.write(parlay_group[['player_names', 'bet_type', 'over/under', 'stat_threshold', 'odds', 'us_odds', 'edge', 
                                           'position', 'team', 'opp', 'minutes', 'possessions', 'points', 'assists', 'rebounds', 'Total_Odds']])
            else:
                st.error("Not enough bets available to form a parlay with the specified criteria.")

if __name__ == "__main__":
    run_parlay_optimizer_app()
