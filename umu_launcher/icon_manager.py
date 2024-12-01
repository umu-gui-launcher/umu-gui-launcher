import os
import json
import time
import requests
from pathlib import Path
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GdkPixbuf, Gio, GLib, Gdk
from steamgrid_api import SteamGridDB

class IconManager:
    def __init__(self, api_key=None):
        self.icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        self.cache_dir = os.path.expanduser('~/.cache/umu-launcher/icons')
        os.makedirs(self.cache_dir, exist_ok=True)
        self.steamgrid = SteamGridDB(api_key) if api_key else None

    def _paintable_to_pixbuf(self, paintable):
        """Convert a Gtk.IconPaintable to GdkPixbuf"""
        if not paintable:
            return None
            
        # Get the file path from the paintable and load it directly as pixbuf
        icon_file = paintable.get_file()
        if icon_file:
            file_path = icon_file.get_path()
            if file_path:
                try:
                    return GdkPixbuf.Pixbuf.new_from_file_at_size(file_path, 64, 64)
                except Exception as e:
                    print(f"Error loading pixbuf from file: {e}")
                    return None
        
        return None

    def search_icons(self, query, callback=None):
        """Search for icons in SteamGridDB"""
        results = []
        
        # Search SteamGridDB
        try:
            icons = self.search_steamgrid(query)
            for icon in icons:
                icon_url = icon.get('url')
                if icon_url:
                    # Generate a cache filename
                    cache_filename = os.path.join(self.cache_dir, f"steamgrid_{hash(icon_url)}.png")
                    results.append({
                        'name': query,
                        'category': 'games',
                        'filename': cache_filename,
                        'url': icon_url,
                        'source': 'steamgrid'
                    })
        except Exception as e:
            print(f"Error searching SteamGridDB: {e}")
        
        if callback:
            callback(results)
        return results
    
    def get_icon(self, icon_name, callback):
        """Get icon from theme or local file"""
        try:
            # First check if it's a local file path
            if os.path.isfile(icon_name):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(icon_name, 64, 64)
                if pixbuf:
                    callback(pixbuf)
                    return
            
            # Check if it's a SteamGridDB icon (stored in results)
            for result in self.search_icons(icon_name):
                if result.get('source') == 'steamgrid' and result.get('url'):
                    cache_filename = result['filename']
                    
                    # Download if not already cached
                    if not os.path.exists(cache_filename):
                        if not self.download_icon(result['url'], cache_filename):
                            continue
                    
                    # Load the downloaded icon
                    try:
                        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(cache_filename, 64, 64)
                        if pixbuf:
                            callback(pixbuf)
                            return
                    except Exception as e:
                        print(f"Error loading cached icon: {e}")
                        continue
            
            # Try to load from icon theme
            icon_theme_flags = Gtk.IconLookupFlags(0)  # No special flags needed
            icon_paintable = self.icon_theme.lookup_icon(
                icon_name,        # icon name
                [],               # fallbacks
                64,              # size
                1,               # scale
                Gtk.TextDirection.NONE,  # direction
                icon_theme_flags  # flags
            )
            
            if icon_paintable:
                # Convert IconPaintable to GdkPixbuf
                pixbuf = self._paintable_to_pixbuf(icon_paintable)
                if pixbuf:
                    callback(pixbuf)
                    return
            
            callback(None)
            
        except Exception as e:
            print(f"Error getting icon: {e}")
            callback(None)
    
    def search_steamgrid(self, game_name):
        """Search for icons on SteamGridDB for a specific game"""
        try:
            if self.steamgrid:
                games = self.steamgrid.search_games(game_name)
                if games:
                    game_id = games[0]['id']
                    icons = self.steamgrid.get_icons(game_id)
                    # Return only the first 3 icons
                    return icons[:3] if icons else []
        except Exception as e:
            print(f"Error searching SteamGridDB: {e}")
        return []
    
    def download_icon(self, url, cache_filename):
        """Download an icon from SteamGridDB and cache it"""
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            with open(cache_filename, 'wb') as f:
                f.write(response.content)
            
            return True
        except Exception as e:
            print(f"Error downloading icon: {e}")
            return False
    
    def get_default_icon(self):
        """Get default application icon"""
        try:
            icon_theme_flags = Gtk.IconLookupFlags(0)  # No special flags needed
            icon_paintable = self.icon_theme.lookup_icon(
                'application-x-executable',        # icon name
                [],               # fallbacks
                64,              # size
                1,               # scale
                Gtk.TextDirection.NONE,  # direction
                icon_theme_flags  # flags
            )
            if icon_paintable:
                # Convert IconPaintable to GdkPixbuf
                return self._paintable_to_pixbuf(icon_paintable)
        except Exception as e:
            print(f"Error getting default icon: {e}")
        return None

    def clear_cache(self):
        """Clear the icon cache directory"""
        try:
            import shutil
            if os.path.exists(self.cache_dir):
                shutil.rmtree(self.cache_dir)
                os.makedirs(self.cache_dir, exist_ok=True)
        except Exception as e:
            print(f"Error clearing icon cache: {e}")
