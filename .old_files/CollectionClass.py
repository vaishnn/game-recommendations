import requests
import time
import yaml
import os
from dotenv import load_dotenv


class CollectingData:
    """
    Just For Collecting Data
    """
    def __init__(self, RatingMin: float,
            YearReleased: float,
            Niche: bool,
            platform: str,
            yaml_file: str,
            api_key: str,
            yaml_filter_file: str) -> None:
        self.RatingMin = RatingMin
        self.YearReleased = YearReleased
        self.Niche = Niche
        self.endpoints = {}
        self.platform = platform
        self.yaml_file = yaml_file
        self.api_key = api_key
        self.yaml_filter_file = yaml_filter_file
        self.list_of_games = []

    def readYaml(self):
        with open(self.yaml_file, 'r') as file:
            self.endpoints = yaml.safe_load(file)

        with open(self.yaml_filter_file, 'r') as file:
            self.filters = yaml.safe_load(file)

    def get_list_of_games(self):
        try:
            response = requests.get(self.endpoints["app"]["get_app_list"])
            response.raise_for_status()
            all_apps = response.json().get('applist', {}).get('apps', [])
            self.list_of_games = all_apps
        except requests.exceptions.RequestException as e:
            print(f"Error fetching the list of all apps: {e}")
            self.list_of_games = []

        # Appying Some Filters
        filters = self.filters['base_data']['filter']
        self.list_of_games = [
            game for game in self.list_of_games
            if all(f not in game['name'].lower() for f in filters)
        ]
        print(len(self.list_of_games))

if __name__ == "__main__":
    load_dotenv()
    api_key = os.getenv("STEAM_API_KEY")
    print(api_key)
    data = CollectingData(4.5, 2020, True, "PC", "end_points.yaml", "YOUR API Key", "filter.yaml")
    data.readYaml()
    data.get_list_of_games()
