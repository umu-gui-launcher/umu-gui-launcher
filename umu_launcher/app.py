import os
import json
import signal
import subprocess
import gi
import time
import logging
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gio, GLib

from .game_info import GameInfo
from .config_window import ConfigWindow
from .game_list import GameList
from .utils import is_windows_executable
from .log_window import LogWindow

logger = logging.getLogger('umu-launcher')

class UmuRunLauncher(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id='com.github.umu_run_launcher',
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        
        self.version = "1.0.0"  # Add version number
        
        self.window = None
        self.game_list = None
        self.games = []
        self.shared_log_window = None
        
        # Initialize default config
        self.config = {
            'games': [],
            'flags': {
                'fullscreen': True,
                'virtual_desktop': True,
                'borderless': True,
                'gamemode': True,
                'mangohud': True,
                'additional_flags': '',
                'wineprefix': os.path.expanduser('~/.wine').strip(),  # Default WINEPREFIX
                'protonpath': os.path.expanduser('~/.local/share/Steam/compatibilitytools.d/UMU-Latest').strip(),  # Default PROTONPATH
                'store': 'egs',  # Default store (egs for Epic Games Store)
                'gameid': 'umu-dauntless'  # Default GAMEID for umu-run
            },
            'steamgriddb_api_key': ''  # API key should be set by user
        }
        
        # Load config and setup monitor
        self.load_config()
        self.setup_config_monitor()
        logger.debug("Initializing UMU Launcher")

    def setup_config_monitor(self):
        """Setup file monitor for config.json"""
        try:
            config_dir = os.path.expanduser("~/.config/umu-launcher")
            os.makedirs(config_dir, exist_ok=True)
            config_file = os.path.join(config_dir, "config.json")
            
            self.config_monitor = Gio.File.new_for_path(config_file).monitor_file(
                Gio.FileMonitorFlags.NONE,
                None
            )
            
            # Add a small delay to prevent rapid reloading
            self._config_changed_source_id = None
            
            def on_config_changed(monitor, file, other_file, event_type):
                if event_type == Gio.FileMonitorEvent.CHANGED:
                    # Cancel any pending reload
                    if self._config_changed_source_id:
                        GLib.source_remove(self._config_changed_source_id)
                    
                    # Schedule a new reload with delay
                    self._config_changed_source_id = GLib.timeout_add(
                        500,  # 500ms delay
                        self._delayed_config_reload
                    )
            
            self.config_monitor.connect('changed', on_config_changed)
            
        except Exception as e:
            logger.error("Error setting up config monitor: %s", e)
    
    def _delayed_config_reload(self):
        """Reload config after a delay to prevent rapid reloading"""
        try:
            # Store current games list
            old_games = self.config.get('games', [])
            
            # Load new config
            self.load_config()
            
            # Update UI if games list changed
            new_games = self.config.get('games', [])
            if old_games != new_games and self.game_list:
                self.game_list.clear()
                self.load_saved_games()
            
            logger.debug("Config reloaded successfully")
            
        except Exception as e:
            logger.error("Error reloading config: %s", e)
        
        # Clear the source ID
        self._config_changed_source_id = None
        return False  # Don't repeat

    def do_startup(self):
        Gtk.Application.do_startup(self)
        
        # Add actions
        action = Gio.SimpleAction.new("quit", None)
        action.connect("activate", self.on_quit)
        self.add_action(action)
        
        action = Gio.SimpleAction.new("add_game", None)
        action.connect("activate", lambda *_: self.on_add_game_clicked(None))
        self.add_action(action)
        
        action = Gio.SimpleAction.new("settings", None)
        action.connect("activate", lambda *_: self.on_settings_clicked(None))
        self.add_action(action)
        
        action = Gio.SimpleAction.new("toggle_layout", None)
        action.connect("activate", self.on_toggle_layout)
        self.add_action(action)
        
        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.on_about_clicked)
        self.add_action(action)

    def do_activate(self):
        logger.debug("Creating main window")
        # Only create window if one doesn't exist
        if not self.window:
            # Create the main window
            self.window = Gtk.ApplicationWindow(application=self)
            self.window.set_title('Umu-Run Games Launcher')
            self.window.set_default_size(900, 700)

            # Add CSS styling
            css_provider = Gtk.CssProvider()
            css_provider.load_from_data(b"""
                .header-bar {
                    padding: 6px;
                    background: alpha(currentColor, 0.05);
                    border-bottom: 1px solid alpha(currentColor, 0.1);
                }
                .header-title {
                    font-weight: bold;
                    font-size: 16px;
                }
                .header-button {
                    padding: 6px;
                    border-radius: 6px;
                }
                .header-button:hover {
                    background: alpha(currentColor, 0.1);
                }
                .header-button.error:hover {
                    background: #FF0000;
                    color: white;
                }
                .main-content {
                    background: @theme_bg_color;
                }
                .empty-state {
                    margin: 48px;
                    padding: 24px;
                    border-radius: 12px;
                    background: alpha(currentColor, 0.05);
                }
                .empty-state-icon {
                    opacity: 0.5;
                    margin-bottom: 12px;
                }
                .empty-state-title {
                    font-size: 24px;
                    font-weight: bold;
                    margin-bottom: 12px;
                }
                .empty-state-description {
                    font-size: 14px;
                    opacity: 0.7;
                    margin-bottom: 24px;
                }
            """)
            display = self.window.get_display()
            Gtk.StyleContext.add_provider_for_display(
                display,
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

            # Create header bar
            self.create_header_bar()
            self.window.set_titlebar(self.header)

            # Create main content box
            main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            main_box.add_css_class('main-content')
            self.window.set_child(main_box)

            # Create game list
            self.game_list = GameList(self, display)
            main_box.append(self.game_list)

            # Load saved games
            self.load_saved_games()

        # Present the window
        self.window.present()

    def create_header_bar(self):
        """Create the header bar with menu"""
        self.header = Gtk.HeaderBar()
        
        # Create menu button
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        
        # Create menu model with only About option
        menu = Gio.Menu()
        section = Gio.Menu()
        section.append("About", "app.about")
        menu.append_section(None, section)
        
        # Create popover
        popover = Gtk.PopoverMenu()
        popover.set_menu_model(menu)
        menu_button.set_popover(popover)
        
        # Add menu button to header
        self.header.pack_end(menu_button)
        
        # Add game button
        add_button = Gtk.Button()
        add_button.set_icon_name("list-add-symbolic")
        add_button.connect("clicked", self.on_add_game_clicked)
        self.header.pack_start(add_button)
        
        # Add log window toggle button
        self.log_button = Gtk.Button()
        self.log_button.set_icon_name("utilities-terminal-symbolic")
        self.log_button.set_tooltip_text("Toggle Log Window")
        self.log_button.add_css_class('header-button')
        self.log_button.connect('clicked', self.on_log_button_clicked)
        self.header.pack_start(self.log_button)
        
        # Add view toggle button
        self.view_button = Gtk.Button()
        self.view_button.set_icon_name("view-grid-symbolic")
        self.view_button.set_tooltip_text("Toggle View (List/Grid)")
        self.view_button.add_css_class('header-button')
        self.view_button.connect('clicked', self.on_view_button_clicked)
        self.header.pack_start(self.view_button)
        
        # Add title
        title_label = Gtk.Label(label="Umu-Run Games Launcher")
        title_label.add_css_class('header-title')
        self.header.set_title_widget(title_label)
        
        # Create box for right-side buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        # Kill All Games button
        kill_button = Gtk.Button()
        kill_button.set_icon_name("process-stop-symbolic")
        kill_button.add_css_class('header-button')
        kill_button.add_css_class('error')
        kill_button.set_tooltip_text("Kill All Running Games")
        kill_button.connect('clicked', self.kill_all_games)
        button_box.append(kill_button)
        
        # Settings button
        settings_button = Gtk.Button()
        settings_button.set_icon_name("emblem-system-symbolic")
        settings_button.set_tooltip_text("Settings")
        settings_button.add_css_class('header-button')
        settings_button.connect('clicked', self.on_settings_clicked)
        button_box.append(settings_button)
        
        self.header.pack_end(button_box)

    def load_config(self):
        """Load configuration from config.json"""
        logger.debug("Loading configuration from %s", os.path.expanduser("~/.config/umu-launcher/config.json"))
        try:
            config_dir = os.path.expanduser("~/.config/umu-launcher")
            os.makedirs(config_dir, exist_ok=True)
            config_file = os.path.join(config_dir, "config.json")
            
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    loaded_config = json.load(f)
                    
                    # Update config with loaded values, preserving defaults for missing keys
                    if 'games' in loaded_config:
                        self.config['games'] = loaded_config['games']
                    if 'flags' in loaded_config:
                        for key, value in loaded_config['flags'].items():
                            if key in self.config['flags']:
                                self.config['flags'][key] = value
                    if 'steamgriddb_api_key' in loaded_config:
                        self.config['steamgriddb_api_key'] = loaded_config['steamgriddb_api_key']
            
            # Save config to ensure it exists and has all default values
            self.save_config()
            
        except Exception as e:
            logger.error("Error loading config: %s", e)
            # Keep using default config
            self.save_config()

    def save_config(self):
        """Save configuration to file"""
        logger.debug("Saving configuration to %s", os.path.expanduser("~/.config/umu-launcher/config.json"))
        try:
            config_dir = os.path.expanduser("~/.config/umu-launcher")
            os.makedirs(config_dir, exist_ok=True)
            config_file = os.path.join(config_dir, "config.json")
            
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
                
            logger.debug("Configuration saved successfully")
            
        except Exception as e:
            logger.error("Error saving config: %s", e)

    def launch_game(self, game_path):
        """Launch a specific game by path"""
        # Find game in config
        game_config = None
        for game in self.config.get('games', []):
            if isinstance(game, dict) and game.get('path') == game_path:
                game_config = game
                break
        
        if game_config:
            # Create game info from config
            from .game_info import GameInfo
            game = GameInfo(game_path)
            game.name = game_config.get('name', '')
            game.icon = game_config.get('icon')
            
            # Set flags from config
            flags = game_config.get('flags', {})
            game.gamemode = flags.get('gamemode', False)
            game.mangohud = flags.get('mangohud', False)
            game.fullscreen = flags.get('fullscreen', False)
            game.virtual_desktop = flags.get('virtual_desktop', False)
            game.borderless = flags.get('borderless', False)
            game.additional_flags = flags.get('additional_flags', '')
            
            # Launch the game
            from .game_list import GameList
            GameList.launch_game(game)
            return 0
        else:
            logger.error("Game not found in configuration: %s", game_path)
            return 1

    def on_add_game_clicked(self, button):
        dialog = Gtk.FileChooserDialog(
            title="Select Game Executable",
            transient_for=self.window,
            modal=True,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            "_Cancel", Gtk.ResponseType.CANCEL,
            "_Add", Gtk.ResponseType.ACCEPT
        )

        # Add file filters more efficiently
        filter_exe = Gtk.FileFilter()
        filter_exe.set_name("Windows Executables")
        filter_exe.add_suffix("exe")  # More efficient than add_pattern
        dialog.add_filter(filter_exe)

        # Set current folder to home directory for faster initial load
        dialog.set_current_folder(Gio.File.new_for_path(os.path.expanduser("~")))

        dialog.connect('response', self.on_file_chosen)
        dialog.present()

    def on_file_chosen(self, dialog, response):
        try:
            if response == Gtk.ResponseType.ACCEPT:
                file_path = dialog.get_file().get_path()
                
                # Verify it's a Windows executable
                if not is_windows_executable(file_path):
                    self.show_error_dialog("Selected file is not a valid Windows executable")
                    return

                # Check if game is already in the list
                for game_config in self.config.get('games', []):
                    if isinstance(game_config, dict) and game_config.get('path') == file_path:
                        self.show_error_dialog("This game is already in your library")
                        return

                # Create new game info
                game_info = GameInfo(file_path)
                
                # Show config window for the new game
                from .game_config_window import GameConfigWindow
                def on_game_updated(updated_game, confirmed):
                    if confirmed:
                        # Only add the game if user clicked Save
                        self.games.append(game_info)
                        
                        # Save to config
                        if 'games' not in self.config:
                            self.config['games'] = []
                        self.config['games'].append({
                            'path': file_path,
                            'name': game_info.name,
                            'icon': game_info.icon,
                            'flags': self.config['flags'].copy()  # Use global settings as defaults
                        })
                        self.save_config()
                        
                    # Refresh the list
                    self.game_list.refresh()
                
                config_window = GameConfigWindow(
                    self.window,
                    game_info,
                    self.game_list.icon_manager,
                    on_game_updated
                )
                config_window.present()
        finally:
            dialog.destroy()

    def load_saved_games(self):
        """Load saved games from config"""
        try:
            self.games = []
            for game_config in self.config.get('games', []):
                if isinstance(game_config, dict):
                    game_path = game_config.get('path')
                    if game_path and os.path.exists(game_path):
                        self.games.append(GameInfo(
                            game_path,
                            name=game_config.get('name'),
                            icon=game_config.get('icon')
                        ))
                elif isinstance(game_config, str) and os.path.exists(game_config):
                    # Handle old format for backward compatibility
                    self.games.append(GameInfo(game_config))
            
            # Update UI
            if self.game_list:
                self.game_list.refresh()
                
            # Convert old format to new format
            updated = False
            for i, game_config in enumerate(self.config.get('games', [])):
                if isinstance(game_config, str):
                    game_info = GameInfo(game_config)
                    self.config['games'][i] = {
                        'path': game_config,
                        'name': game_info.name,
                        'icon': game_info.icon,
                        'flags': {
                            'gamemode': False,
                            'mangohud': False,
                            'fullscreen': False,
                            'virtual_desktop': False,
                            'borderless': False,
                            'additional_flags': ''
                        }
                    }
                    updated = True
            if updated:
                self.save_config()
                
        except Exception as e:
            logger.error("Error loading saved games: %s", e)
            self.show_error_dialog(f"Error loading saved games: {str(e)}")

    def on_settings_clicked(self, button):
        settings = ConfigWindow(self.window, self.config, self.on_settings_saved)
        settings.present()

    def on_settings_saved(self, new_config):
        self.config = new_config
        self.save_config()

    def kill_all_games(self, button=None):
        killed_any = False
        
        try:
            # First try to kill all tracked games
            for game in self.games:
                if game.is_running():
                    game.stop()
                    killed_any = True
            
            # Find and kill all Wine processes
            try:
                # Get all Wine processes
                wine_pids = []
                processes = [
                    'wine64-preloader',
                    'wine64',
                    'wine-preloader',
                    'wine',
                    'wineserver'
                ]
                
                for proc in processes:
                    try:
                        output = subprocess.check_output(['pgrep', '-f', proc], text=True)
                        pids = output.strip().split('\n')
                        wine_pids.extend([pid for pid in pids if pid])
                    except subprocess.CalledProcessError:
                        continue
                
                if wine_pids:
                    killed_any = True
                    logger.info("Found Wine processes: %s", wine_pids)
                    
                    # First try SIGTERM
                    for pid in wine_pids:
                        try:
                            os.kill(int(pid), signal.SIGTERM)
                            logger.info("Sent SIGTERM to process %s", pid)
                        except ProcessLookupError:
                            pass
                    
                    # Wait a bit for processes to terminate
                    time.sleep(1)
                    
                    # Then force kill any remaining processes
                    for pid in wine_pids:
                        try:
                            os.kill(int(pid), signal.SIGKILL)
                            logger.info("Sent SIGKILL to process %s", pid)
                        except ProcessLookupError:
                            pass
                
                # Finally, kill any remaining umu-run processes
                try:
                    output = subprocess.check_output(['pgrep', '-f', 'umu-run'], text=True)
                    umu_pids = output.strip().split('\n')
                    
                    if umu_pids:
                        killed_any = True
                        for pid in umu_pids:
                            if pid:
                                try:
                                    logger.info("Killing umu-run process: %s", pid)
                                    os.kill(int(pid), signal.SIGKILL)
                                except ProcessLookupError:
                                    pass
                except subprocess.CalledProcessError:
                    pass
                
            except Exception as e:
                logger.error("Error killing Wine processes: %s", e)
                self.show_error_dialog(str(e))
        
        except Exception as e:
            logger.error("Error in kill_all_games: %s", e)
            self.show_error_dialog(str(e))
            return
        
        # Refresh the list to update stop buttons
        if killed_any:
            logger.info("Games killed, refreshing list")
            self.game_list.refresh(self.games)
        else:
            logger.info("No running games found")
            dialog = Gtk.MessageDialog(
                transient_for=self.window,
                modal=True,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="No running games found"
            )
            dialog.connect('response', lambda d, r: d.destroy())
            dialog.present()

    def show_error_dialog(self, message):
        # Find the active window
        active_window = None
        if self.window and self.window.is_visible():
            active_window = self.window
        
        dialog = Gtk.MessageDialog(
            transient_for=active_window,
            modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=message
        )
        dialog.connect('response', lambda d, r: d.destroy())
        dialog.present()

    def create_log_window(self):
        """Create the shared log window without showing it"""
        if not self.shared_log_window:
            # Create shared log window if it doesn't exist
            from .log_window import LogWindow
            self.shared_log_window = LogWindow(
                parent=self.window,
                width=800,
                height=400,
                position='right'
            )
            self.shared_log_window.title_label.set_text("Application Log")
            
            # Add welcome message
            self.shared_log_window.append_text("=== Umu-Run Games Launcher Log ===\n")
            self.shared_log_window.append_text(f"Started at {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        return self.shared_log_window

    def on_log_button_clicked(self, button):
        """Handle log window toggle button click"""
        # Create window if it doesn't exist
        if not self.shared_log_window:
            self.create_log_window()
        
        # Toggle window visibility with animation
        if self.shared_log_window.is_visible():
            self.shared_log_window.hide_with_animation()
            self.log_button.remove_css_class('suggested-action')
        else:
            self.shared_log_window.show_with_animation()
            self.log_button.add_css_class('suggested-action')

    def on_view_button_clicked(self, button):
        """Handle view toggle button click"""
        if hasattr(self, 'game_list'):
            is_grid = self.game_list.toggle_layout()
            # Update button icon based on next view
            if is_grid:
                button.set_icon_name("view-list-symbolic")
                button.set_tooltip_text("Switch to List View")
            else:
                button.set_icon_name("view-grid-symbolic")
                button.set_tooltip_text("Switch to Grid View")

    def on_toggle_layout(self, action, param):
        """Toggle between vertical and horizontal layout"""
        if hasattr(self, 'game_list'):
            self.game_list.toggle_layout()

    def on_about_clicked(self, action, param):
        """Show the about dialog"""
        dialog = Gtk.AboutDialog()
        dialog.set_transient_for(self.window)
        dialog.set_modal(True)
        
        dialog.set_program_name("UMU Launcher")
        dialog.set_version(self.version)
        dialog.set_authors(["Hamza"])
        dialog.set_comments("A game launcher for running Windows games on Linux")
        dialog.set_logo_icon_name("applications-games")
        
        dialog.present()

    def on_quit(self, action, param):
        """Quit the application"""
        self.quit()
