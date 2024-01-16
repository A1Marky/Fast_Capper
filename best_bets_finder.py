import pandas as pd

# Assuming merged_df is your merged dataframe
merged_df = pd.read_csv('merged_dataframes.csv')  # Replace with your actual file path

# Filter the dataframe for rows with relevant betting information
betting_df = merged_df.dropna(subset=['bet_type', 'over/under', 'odds', 'stat_threshold'])

# Function to identify best bets based on projections and betting thresholds
def identify_best_bets(df, stat_column, bet_type_prefix):
    best_bets = []
    for _, row in df.iterrows():
        if bet_type_prefix in row['bet_type']:
            stat_projection = row[stat_column]
            stat_threshold = row['stat_threshold']

            if 'Over' in row['over/under'] and stat_projection > stat_threshold:
                best_bets.append(row)
            elif 'Under' in row['over/under'] and stat_projection < stat_threshold:
                best_bets.append(row)
    
    return pd.DataFrame(best_bets)

# Identify best bets for points, assists, and rebounds
best_bets_points = identify_best_bets(betting_df, 'points', 'player_points')
best_bets_assists = identify_best_bets(betting_df, 'assists', 'player_assists')
best_bets_rebounds = identify_best_bets(betting_df, 'rebounds', 'player_rebounds')

# Combine best bets into one dataframe
best_bets_combined = pd.concat([best_bets_points, best_bets_assists, best_bets_rebounds])

# Display or further process the best bets dataframe
best_bets_combined.to_csv('best_bets.csv', index=False)