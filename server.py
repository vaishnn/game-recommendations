from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv
import pandas as pd
import pickle

load_dotenv()
app = Flask(__name__)
CORS(app)

try:
    df = pickle.load(open('dataframe.pkl', 'rb'))
    cosine_sim = pickle.load(open('cosine_sim.pkl', 'rb'))
    id_to_index = pickle.load(open('id_to_index.pkl', 'rb'))
    print(">>> ML Model components loaded successfully! <<<")
except FileNotFoundError:
    print(">>> FATAL: Model files (dataframe.pkl, cosine_sim.pkl, id_to_index.pkl) not found. <<<")
    exit()


STEAM_API_KEY = os.getenv("STEAM_API_KEY")

def get_advanced_recommendations(input_games: list, niche_factor: float, cosine_sim_matrix, dataframe, id_map):
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

    total_scores = total_scores.drop(input_game_indices, errors='ignore')
    top_10_indices = total_scores.sort_values(ascending=False).head(10).index

    return dataframe.iloc[top_10_indices]


@app.route('/api/get-games', methods=['GET'])
def get_owned_games():
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


@app.route('/api/recommend', methods=['POST'])
def recommend():
    data = request.get_json()
    print(data)
    if not data or 'input_games' not in data or 'niche_factor' not in data:
        return jsonify({"error": "Invalid request. Missing 'input_games' or 'niche_factor'."}), 400

    input_games = data['input_games']
    niche_factor = data['niche_factor']

    recommendations_df = get_advanced_recommendations(
        input_games,
        niche_factor,
        cosine_sim_matrix=cosine_sim,
        dataframe=df,
        id_map=id_to_index
    )

    recommendations_list = recommendations_df[['id', 'name', 'short_description']].to_dict('records')

    return jsonify(recommendations_list)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4000, debug=True)
