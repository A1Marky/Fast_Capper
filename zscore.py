import pandas as pd
from scipy.stats import norm

# Function to convert American odds to implied probability
def american_odds_to_probability(american_odds):
    if american_odds > 0:
        return 100 / (american_odds + 100)
    else:
        return -american_odds / (-american_odds + 100)

# Function to calculate the Kelly criterion fraction
def kelly_criterion(implied_prob, american_odds, bankroll):
    if american_odds > 0:
        b = american_odds / 100
    else:
        b = -100 / american_odds
    p = implied_prob
    q = 1 - p
    f_star = (b * p - q) / b
    bet_amount = f_star * bankroll
    return max(bet_amount, 0)  # Ensure the bet amount is not negative

# Function to calculate implied probability from actual stat projections
def calculate_implied_probability_from_actual_stats(row, scoring_rules, bet_type_to_stat):
    bet_type = row['bet_type']
    if bet_type in bet_type_to_stat:
        stat = bet_type_to_stat[bet_type]
        stat_projection = row[stat]
        stat_fd_points = stat_projection * scoring_rules.get(stat, 0)  # Default to 0 if stat not in scoring rules
    else:
        return None  # Return None if bet_type is not recognized

    std_stat = row['fd_std'] * scoring_rules.get(stat, 0)
    over_under = row['over/under']
    stat_threshold = row['stat_threshold']
    if over_under.lower() == 'over':
        probability = 1 - norm.cdf(stat_threshold, stat_fd_points, std_stat)
    elif over_under.lower() == 'under':
        probability = norm.cdf(stat_threshold, stat_fd_points, std_stat)
    else:
        return None

    return probability

# Function to calculate edge and expected value (EV)
def calculate_edge_and_ev(implied_prob, sportsbook_prob, bet_size):
    edge = implied_prob - sportsbook_prob
    ev = (implied_prob * (bet_size * (1 / sportsbook_prob - 1))) - (1 - implied_prob) * bet_size
    return edge, ev

# FanDuel scoring rules and bet type to stat mapping
scoring_rules = {
    'points': 1,
    'assists': 1.5,
    'rebounds': 1.2,
    'blocks': 3,
    'steals': 3,
    'three_pt_fg': 3
}
bet_type_to_stat = {
    'player_assists': 'assists',
    'player_assists_alternate': 'assists',
    'player_points': 'points',
    'player_points_alternate': 'points',
    'player_rebounds': 'rebounds',
    'player_rebounds_alternate': 'rebounds',
    'player_threes': 'three_pt_fg',
    'player_threes_alternate': 'three_pt_fg',
    'player_blocks': 'blocks',
    'player_blocks_alternate': 'blocks',
    'player_steals': 'steals',
    'player_steals_alternate': 'steals'
}

# Load the dataset
file_path = 'master_df.csv'
master_df = pd.read_csv(file_path)

# Set your bankroll
bankroll = 10  # Example bankroll, adjust as needed

# Calculate sportsbook implied probability
master_df['sportsbook_prob'] = master_df['us_odds'].apply(american_odds_to_probability)

# Calculate implied probabilities, edge, EV, and bet size using Kelly criterion for each bet
for index, row in master_df.iterrows():
    implied_prob = calculate_implied_probability_from_actual_stats(row, scoring_rules, bet_type_to_stat)
    if implied_prob is not None:
        sportsbook_prob = row['sportsbook_prob']
        edge, ev = calculate_edge_and_ev(implied_prob, sportsbook_prob, 1)  # Placeholder bet size
        kelly_bet_size = kelly_criterion(implied_prob, row['us_odds'], bankroll)
        
        master_df.at[index, 'implied_probability'] = implied_prob
        master_df.at[index, 'edge'] = edge
        master_df.at[index, 'ev'] = ev
        master_df.at[index, 'kelly_bet_size'] = kelly_bet_size

# Calculate mean and standard deviation for edge, EV, and implied probability
edge_mean = master_df['edge'].mean()
edge_std = master_df['edge'].std()
ev_mean = master_df['ev'].mean()
ev_std = master_df['ev'].std()
ip_mean = master_df['implied_probability'].mean()
ip_std = master_df['implied_probability'].std()

# Function to calculate the composite z-score rating
def calculate_composite_z_score(row):
    edge_z = (row['edge'] - edge_mean) / edge_std
    ev_z = (row['ev'] - ev_mean) / ev_std
    ip_z = (row['implied_probability'] - ip_mean) / ip_std
    return (edge_z + ev_z + ip_z) / 3  # Averaging the z-scores

# Apply the function to calculate the composite score
master_df['composite_z_score'] = master_df.apply(calculate_composite_z_score, axis=1)

# Select relevant columns to display, including the composite z-score and Kelly bet size
output_columns = [
    'player_names', 'team', 'bet_type', 'over/under', 'stat_threshold', 'odds', 'us_odds',
    'implied_probability', 'sportsbook_prob', 'edge', 'ev', 'composite_z_score', 'kelly_bet_size'
]

# Output the processed DataFrame with calculated probabilities, edge, EV, composite z-score, and Kelly bet size
output_df = master_df[output_columns]

# Display the first few rows of the output DataFrame, including the composite z-score
print(output_df.head())

# Save the output DataFrame to a CSV file
output_df.to_csv('output_df.csv', index=False)
