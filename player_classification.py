import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
import seaborn as sns

# Load the dataset
df = pd.read_csv('all_players_df.csv')

# Create combined stats for prop bets involving multiple categories.
df['combined_points_rebounds_assists'] = df['points'] + df['rebounds'] + df['assists']
df['combined_points_rebounds'] = df['points'] + df['rebounds']
df['combined_points_assists'] = df['points'] + df['assists']
df['combined_rebounds_assists'] = df['rebounds'] + df['assists']

# Selecting relevant features for clustering including the new combined stats
features = [
    'points', 'rebounds', 'assists', 'three_pt_fg', 'blocks', 'steals', 'turnovers', 
    'combined_points_rebounds_assists', 'combined_points_rebounds', 'combined_points_assists', 
    'combined_rebounds_assists'
]

# Extracting the relevant features for clustering
cluster_data = df[features]

# Handling missing values and normalizing the data
cluster_data.fillna(cluster_data.mean(), inplace=True)
scaler = StandardScaler()
cluster_data_normalized = scaler.fit_transform(cluster_data)

# Applying K-Means Clustering with an optimal number of clusters determined by the Elbow Method
kmeans = KMeans(n_clusters=4, random_state=1)
cluster_labels = kmeans.fit_predict(cluster_data_normalized)

# Adding the cluster labels to the dataset
df['type_of_player'] = cluster_labels

# Analyzing the centroids of each cluster to determine "player_type" labels
centroids = kmeans.cluster_centers_
centroid_df = pd.DataFrame(scaler.inverse_transform(centroids), columns=features)

# Interpretation of each cluster based on the centroids
player_types = {
    0: {"label": "Role Player", "bet": "Bets with lower thresholds, possibly turnovers or steals"},
    1: {"label": "Defensive Anchor", "bet": "Rebound or block-related bets, or a double-double with points and rebounds"},
    2: {"label": "Balanced Contributor", "bet": "Combined points, rebounds, and assists bets"},
    3: {"label": "Offensive Leader", "bet": "Points-related bets, assists, or three-point shots made"}
}

# Assigning the 'player_type' and 'best_suited_bet' based on the clusters
df['player_type'] = df['type_of_player'].apply(lambda x: player_types[x]['label'])
df['best_suited_bet'] = df['type_of_player'].apply(lambda x: player_types[x]['bet'])

# Optionally, display the DataFrame with the new columns
print(df[['player_names', 'type_of_player', 'player_type', 'best_suited_bet']].head())

# Saving the DataFrame to a new CSV file if needed
df.to_csv('all_players_with_player_types_to_bet_type.csv', index=False)
