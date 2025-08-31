# --- Import necessary libraries ---
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv
import pandas as pd
import pickle
import sys

# --- Initial Setup ---
load_dotenv()
app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# --- Load the Machine Learning Model Components ---
# This is done once when the server starts up for maximum efficiency.
try:
    df = pickle.load(open('dataframe.pkl', 'rb'))
    cosine_sim = pickle.load(open('cosine_sim.pkl', 'rb'))
    id_to_index = pickle.load(open('id_to_index.pkl', 'rb'))
    print(">>> ML Model components loaded successfully! <<<")
except FileNotFoundError:
    print(">>> FATAL: Model files (dataframe.pkl, cosine_sim.pkl, id_to_index.pkl) not found. <<<")
    # In a real application, you might want to handle this more gracefully,
    # but for this purpose, exiting is fine if the core component is missing.
    exit()


# Retrieve the Steam API key from the environment variables
STEAM_API_KEY = os.getenv("STEAM_API_KEY")

# --- Recommendation Function (Copied from your ML script) ---
def get_advanced_recommendations(input_games: list, niche_factor: float, cosine_sim_matrix, dataframe, id_map):
    """
    Generates recommendations based on multiple game IDs and a niche/popularity factor.
    """
    total_scores = pd.Series(0.0, index=dataframe.index)
    input_game_indices = []

    for game in input_games:
        game_id = game['id']
        multiplier = game.get('multiplier', 1.0)
        pref_type = game.get('type', 'like')

        if game_id not in id_map:
            print(f"Warning: Game with ID '{game_id}' not found. Skipping.")
            continue

        idx = id_map[game_id]
        input_game_indices.append(idx)

        sim_scores = cosine_sim_matrix[idx]
        adjusted_scores = -sim_scores if pref_type == 'opposite' else sim_scores
        total_scores += (adjusted_scores * multiplier)

    # The niche_factor directly adjusts the weight of the popularity score.
    # adjustment = 1 + (dataframe['popularity_score'] * niche_factor)
    # total_scores = total_scores * adjustment
    candidate_indices = total_scores.sort_values(ascending=False).head(200).index
    candidates_df = dataframe.iloc[candidate_indices].copy()
    print(10)
    candidates_df['total_reviews'] = candidates_df['positive_reviews'] + candidates_df['negative_reviews']
    print(niche_factor, flush=True)
    # CRITICAL: Check if the 'total_reviews' column exists
    if 'total_reviews' not in candidates_df.columns:
        print("WARNING: 'total_reviews' column not found. Niche factor will not work correctly.")
        # Fallback to the top 10 if the column is missing
        return candidates_df.head(10)

    # 2. Based on niche_factor, filter or re-rank the candidates
    if niche_factor <= -0.5:  # Find "very niche" games
        # Filter for games with a low number of reviews (e.g., between 50 and 500)
        niche_games = candidates_df[
            (candidates_df['total_reviews'] >= 50) & (candidates_df['total_reviews'] <= 500)
        ]

        # If we found enough niche games, return them.
        # Otherwise, return the most similar games we have.
        if len(niche_games) > 0:
            return niche_games.head(10)
        else:
            return candidates_df.head(10)


    elif niche_factor >= 0.5:  # Find "very famous" games
        # Re-sort the candidates by their review count in descending order
        popular_games = candidates_df.sort_values(by='total_reviews', ascending=False)
        return popular_games.head(10)

    else:  # For a "normal" (balanced) factor close to 0
        # Return the original top 10 based purely on game similarity
        return candidates_df.head(10)



# --- API Route Definitions ---

# This is your existing route to get a user's game library. It remains unchanged.
@app.route('/api/get-games', methods=['GET'])
def get_owned_games():
    """Acts as a secure proxy to get a user's owned games from the Steam API."""
    steamid = request.args.get('steamid')
    print(steamid)
    if not steamid:
        return jsonify({"error": "SteamID is required"}), 400

    if not STEAM_API_KEY:
        print("ERROR: STEAM_API_KEY environment variable not set.")
        return jsonify({"error": "Server configuration error: API key not found"}), 500

    api_url = f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={STEAM_API_KEY}&steamid={steamid}&format=json&include_appinfo=true"

    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()

        if "response" not in data or "games" not in data["response"]:
            return jsonify({"error": "Could not retrieve game library. The user profile may be private or empty."}), 404

        return jsonify(data["response"])

    except requests.exceptions.RequestException as e:
        print(f"Error calling Steam API: {e}")
        return jsonify({"error": "Failed to fetch data from Steam API"}), 502


# --- NEW: API Route for Machine Learning Recommendations ---
@app.route('/api/recommend', methods=['POST'])
def recommend():
    """
    Receives user's game selections and returns model-driven recommendations.
    """
    # Get the JSON data sent from the JavaScript frontend
    data = request.get_json()
    print(data)
    # Validate the incoming data
    if not data or 'input_games' not in data or 'niche_factor' not in data:
        return jsonify({"error": "Invalid request. Missing 'input_games' or 'niche_factor'."}), 400

    input_games = data['input_games']
    niche_factor = data['niche_factor']

    # Get the recommendations from the model
    recommendations_df = get_advanced_recommendations(
        input_games,
        niche_factor,
        cosine_sim_matrix=cosine_sim,
        dataframe=df,
        id_map=id_to_index
    )

    # Convert the resulting DataFrame to a list of dictionaries to send back as JSON
    # We select a few key columns to send to the frontend.
    recommendations_list = recommendations_df[['id', 'name', 'short_description']].to_dict('records')

    # Return the recommendations as a JSON response
    return jsonify(recommendations_list)


# --- Running the Server ---
if __name__ == '__main__':
    # Start the Flask server.
    app.run(host='0.0.0.0', port=4000, debug=True)
