from flask import Flask, render_template, request, session
import requests
import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Load API key from environment variable
API_KEY = os.getenv('STEAM_API_KEY')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        steam_id = request.form.get('steam_id')
        if steam_id:
            games_data = get_user_games(steam_id)
            if games_data and 'response' in games_data and 'games' in games_data['response']:
                session['games'] = games_data['response']['games']
                session['game_count'] = games_data['response']['game_count']
            else:
                session['games'] = []
                session['game_count'] = 0
            return render_template('index.html', games=session.get('games'), game_count=session.get('game_count'))

    if 'restart' in request.args:
        session.clear()

    return render_template('index.html', games=session.get('games'), game_count=session.get('game_count'))

def get_user_games(steam_id):
    """Fetches the list of games owned by a Steam user."""
    if not API_KEY:
        print("Error: STEAM_API_KEY not found.")
        return None
    url = f'http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={API_KEY}&steamid={steam_id}&format=json&include_appinfo=1'
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Steam API: {e}")
        return None

if __name__ == '__main__':
    app.run(debug=True)
