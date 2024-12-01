#!/usr/bin/env python3

import sys
import os
from umu_launcher.app import UmuRunLauncher
from steamgrid_api import SteamGridDB
import argparse

class GameList:
    def __init__(self, api_key: str):
        """Initialize GameList with SteamGridDB integration"""
        self.steamgrid = SteamGridDB(api_key)
        
    def search_icons(self, game_name: str):
        """
        Search for game icons using SteamGridDB
        
        Args:
            game_name (str): Name of the game to search icons for
        """
        try:
            # Search for the game
            games = self.steamgrid.search_games(game_name)
            if not games:
                print(f"No games found for: {game_name}")
                return []
                
            # Get icons for the first matching game
            game_id = games[0]['id']
            icons = self.steamgrid.get_icons(game_id)
            if not icons:
                print(f"No icons found for: {game_name}")
            return icons
        except Exception as e:
            print(f"Error searching for icons: {e}")
            return []

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='UMU Game Launcher')
    parser.add_argument('--launch', help='Launch a specific game by path')
    args = parser.parse_args()
    
    app = UmuRunLauncher()
    
    if args.launch:
        # Launch specific game
        app.launch_game(args.launch)
    else:
        # Run normal GUI
        exit_status = app.run(sys.argv)
        sys.exit(exit_status)