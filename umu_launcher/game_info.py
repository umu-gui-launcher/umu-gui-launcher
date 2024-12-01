import os
import time
import signal
import subprocess
import magic
from pathlib import Path

class GameInfo:
    def __init__(self, file_path, name=None, icon=None):
        self.file_path = file_path
        self.name = name if name else self._get_name()
        self.icon = icon if icon else self._get_icon_path()
        self.process = None
        self._size = os.path.getsize(file_path)
        self._determine_type()
        
    def _get_name(self):
        """Get game name from parent folder name"""
        return os.path.basename(os.path.dirname(self.file_path))
        
    def _get_icon_path(self):
        """Get path to game icon if it exists"""
        game_dir = os.path.dirname(self.file_path)
        icon_path = os.path.join(game_dir, "icon.png")
        return icon_path if os.path.exists(icon_path) else None
        
    def set_icon(self, icon_url):
        """Download and set a new icon for the game"""
        try:
            import requests
            game_dir = os.path.dirname(self.file_path)
            icon_path = os.path.join(game_dir, "icon.png")
            
            # Download the icon
            response = requests.get(icon_url)
            response.raise_for_status()
            
            # Save the icon
            with open(icon_path, 'wb') as f:
                f.write(response.content)
            
            self.icon = icon_path
            return True
        except Exception as e:
            print(f"Error setting icon: {e}")
            return False
        
    def _determine_type(self):
        """Determine the type of executable using python-magic"""
        try:
            mime = magic.Magic()
            file_type = mime.from_file(self.file_path)
            if "PE32+" in file_type:
                self.type = "64-bit Windows Executable"
            elif "PE32" in file_type:
                self.type = "32-bit Windows Executable"
            elif "MS-DOS" in file_type:
                self.type = "DOS Executable"
            else:
                self.type = "Unknown Executable"
        except Exception:
            self.type = "Unknown"
            
    def format_size(self):
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self._size < 1024:
                return f"{self._size:.1f} {unit}"
            self._size /= 1024
        return f"{self._size:.1f} TB"
        
    def is_running(self):
        """Check if game is running"""
        return self.process is not None and self.process.poll() is None
        
    def stop(self):
        """Stop the game"""
        if self.is_running():
            os.kill(self.process.pid, signal.SIGTERM)
