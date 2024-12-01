import requests
from typing import List, Dict, Optional

class SteamGridDB:
    BASE_URL = "https://www.steamgriddb.com/api/v2"
    
    def __init__(self, api_key: str):
        """
        Initialize the SteamGridDB API client.
        
        Args:
            api_key (str): Your SteamGridDB API key
        """
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def search_games(self, query: str) -> List[Dict]:
        """
        Search for games in SteamGridDB.
        
        Args:
            query (str): The game title to search for
            
        Returns:
            List[Dict]: List of games matching the search query
        """
        endpoint = f"{self.BASE_URL}/search/autocomplete/{query}"
        response = requests.get(endpoint, headers=self.headers)
        response.raise_for_status()
        return response.json().get('data', [])
    
    def get_icons(self, game_id: int) -> List[Dict]:
        """
        Get icons for a specific game.
        
        Args:
            game_id (int): The SteamGridDB game ID
            
        Returns:
            List[Dict]: List of icons available for the game
        """
        endpoint = f"{self.BASE_URL}/icons/game/{game_id}"
        response = requests.get(endpoint, headers=self.headers)
        response.raise_for_status()
        return response.json().get('data', [])
