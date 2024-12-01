import os
import time
import subprocess
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, GLib, Pango, GdkPixbuf
from pathlib import Path
from .icon_manager import IconManager
from .log_window import LogWindow
import signal
import requests

class GameList(Gtk.Box):
    def __init__(self, app, display):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.icon_manager = IconManager(app.config.get('steamgriddb_api_key'))
        self.log_windows = {}  # Store log windows for each game
        
        # Create scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        
        # Create list box
        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list_box.add_css_class('game-list')
        
        scrolled.set_child(self.list_box)
        self.append(scrolled)
        
        # Add styles
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            .game-list { 
                padding: 12px;
                background: transparent;
            }
            .game-row {
                padding: 12px;
                margin: 8px;
                border-radius: 12px;
                background: alpha(@theme_fg_color, 0.1);
                transition: all 200ms ease;
            }
            .game-row:hover {
                background: alpha(@theme_fg_color, 0.15);
                transform: translateY(-1px);
                box-shadow: 0 2px 4px alpha(black, 0.2);
            }
            .game-icon {
                border-radius: 8px;
                background: alpha(@theme_fg_color, 0.1);
            }
            .game-title {
                font-weight: bold;
                font-size: 16px;
                color: @theme_fg_color;
            }
            .game-path {
                font-size: 12px;
                opacity: 0.7;
                color: @theme_fg_color;
            }
            .game-button {
                padding: 8px 16px;
                border-radius: 6px;
                transition: all 200ms ease;
                color: @theme_fg_color;
            }
            .game-button:hover {
                transform: translateY(-1px);
            }
            .game-button.suggested-action {
                background: #2E8B57;
                color: white;
            }
            .game-button.suggested-action:hover {
                background: #3AA76A;
            }
            .game-button.destructive-action {
                background: #CD5C5C;
                color: white;
            }
            .game-button.destructive-action:hover {
                background: #E06C6C;
            }
            .game-button.configure {
                background: alpha(@theme_fg_color, 0.1);
            }
            .game-button.configure:hover {
                background: alpha(@theme_fg_color, 0.15);
            }
            .running-label {
                font-size: 12px;
                background: #2E8B57;
                color: white;
                padding: 2px 8px;
                border-radius: 12px;
            }
            .empty-state {
                margin: 48px;
                padding: 24px;
                border-radius: 12px;
                background: alpha(@theme_fg_color, 0.1);
            }
            .empty-state-icon {
                color: @theme_fg_color;
                opacity: 0.5;
                margin-bottom: 12px;
            }
            .empty-state-title {
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 12px;
                color: @theme_fg_color;
            }
            .empty-state-description {
                font-size: 14px;
                opacity: 0.7;
                margin-bottom: 24px;
                color: @theme_fg_color;
            }
        """)
        Gtk.StyleContext.add_provider_for_display(
            display,
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    
    def create_game_row(self, game):
        """Create a row for a game in the list"""
        row = Gtk.ListBoxRow()
        row.add_css_class('game-row')
        
        # Create box for game info
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        box.set_margin_start(8)
        box.set_margin_end(8)
        
        # Game icon
        icon = Gtk.Picture()
        icon.set_size_request(64, 64)
        icon.add_css_class('game-icon')
        if game.icon and os.path.exists(game.icon):
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(game.icon, 64, 64)
                icon.set_pixbuf(pixbuf)
            except Exception as e:
                print(f"Error loading icon: {e}")
        box.append(icon)
        
        # Create a box for game info
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        info_box.set_hexpand(True)
        
        # Add game name
        name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        name_label = Gtk.Label(label=game.name)
        name_label.set_halign(Gtk.Align.START)
        name_label.add_css_class("game-title")
        name_box.append(name_label)
        
        # Add running indicator if game is running
        if game.process and game.process.poll() is None:
            running_label = Gtk.Label(label="Running")
            running_label.add_css_class("running-label")
            name_box.append(running_label)
        
        info_box.append(name_box)
        
        # Add game path
        path_label = Gtk.Label(label=game.file_path)
        path_label.set_halign(Gtk.Align.START)
        path_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        path_label.add_css_class("game-path")
        info_box.append(path_label)
        
        box.append(info_box)
        
        # Add buttons box
        buttons_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons_box.set_halign(Gtk.Align.END)
        buttons_box.set_valign(Gtk.Align.CENTER)
        
        # Create launch/stop button
        if game.process and game.process.poll() is None:
            launch_button = Gtk.Button(label="Stop")
            launch_button.add_css_class("game-button")
            launch_button.add_css_class("destructive-action")
        else:
            launch_button = Gtk.Button(label="Launch")
            launch_button.add_css_class("game-button")
            launch_button.add_css_class("suggested-action")
        
        launch_button.connect('clicked', self.on_launch_clicked, game)
        buttons_box.append(launch_button)
        
        # Create configure button
        config_button = Gtk.Button(label="Configure")
        config_button.add_css_class("game-button")
        config_button.add_css_class("configure")
        config_button.connect('clicked', self.on_configure_clicked, game)
        buttons_box.append(config_button)
        
        # Create remove button
        remove_button = Gtk.Button(label="Remove")
        remove_button.add_css_class("game-button")
        remove_button.add_css_class("destructive-action")
        remove_button.connect('clicked', self.on_remove_clicked, game)
        buttons_box.append(remove_button)
        
        box.append(buttons_box)
        row.set_child(box)
        
        return row
        
    def refresh(self):
        """Refresh the game list"""
        # Remove all current rows
        while True:
            row = self.list_box.get_first_child()
            if row is None:
                break
            self.list_box.remove(row)
        
        # Add empty state if no games
        if not self.app.games:
            empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            empty_box.set_halign(Gtk.Align.CENTER)
            empty_box.set_valign(Gtk.Align.CENTER)
            empty_box.add_css_class('empty-state')
            
            # Add icon
            icon = Gtk.Image.new_from_icon_name('applications-games-symbolic')
            icon.set_pixel_size(64)
            icon.add_css_class('empty-state-icon')
            empty_box.append(icon)
            
            # Add title
            title = Gtk.Label(label="No Games Added")
            title.add_css_class('empty-state-title')
            empty_box.append(title)
            
            # Add description
            desc = Gtk.Label(label="Click the '+' button in the top-right to add your first game")
            desc.add_css_class('empty-state-description')
            empty_box.append(desc)
            
            # Add button
            add_button = Gtk.Button(label="Add Game")
            add_button.add_css_class('suggested-action')
            add_button.add_css_class('game-button')
            add_button.connect('clicked', lambda b: self.app.on_add_game_clicked(None))
            empty_box.append(add_button)
            
            row = Gtk.ListBoxRow()
            row.set_child(empty_box)
            self.list_box.append(row)
        else:
            # Add rows for each game
            for game in self.app.games:
                row = self.create_game_row(game)
                self.list_box.append(row)
            
    def check_game_status(self, game):
        """Check if a game is still running and update UI accordingly"""
        try:
            # Check if process has exited
            if game.process and game.process.poll() is not None:
                # Game has stopped
                print(f"Game {game.name} has stopped")
                # Add stop message to log
                if game in self.log_windows:
                    GLib.idle_add(self.log_windows[game].append_text, f"\n=== Game stopped at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                # Clean up any remaining wine processes
                self.stop_game(game)
                return False  # Stop monitoring
            return True  # Continue monitoring
        except Exception as e:
            print(f"Error checking game status: {e}")
            return False  # Stop monitoring on error

    def stop_game(self, game):
        """Stop a running game and its associated processes"""
        try:
            print(f"Stopping game {game.name}")
            
            # Log to shared log window if it exists
            if self.app.shared_log_window:
                self.app.shared_log_window.append_text(f"\n=== Stopping {game.name} at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            
            if game.process and game.process.poll() is None:
                try:
                    # First try to terminate the main process group
                    pid = game.process.pid
                    print(f"Sending SIGTERM to process group {pid}")
                    os.killpg(pid, signal.SIGTERM)
                    
                    # Wait briefly for main process to terminate
                    time.sleep(1)
                    
                    # Find and kill any remaining wine processes
                    try:
                        # Get all wine-related processes
                        wine_procs = subprocess.run(
                            ['pgrep', '-f', r'(wine|\.exe)'],
                            capture_output=True,
                            text=True
                        ).stdout.strip().split('\n')
                        
                        # Send SIGTERM to each wine process
                        for proc_pid in wine_procs:
                            if proc_pid:
                                try:
                                    pid = int(proc_pid)
                                    print(f"Terminating wine process {pid}")
                                    if self.app.shared_log_window:
                                        self.app.shared_log_window.append_text(f"Terminating wine process {pid}\n")
                                    os.kill(pid, signal.SIGTERM)
                                except (ProcessLookupError, ValueError):
                                    pass
                        
                        # Wait for processes to terminate
                        time.sleep(2)
                        
                        # Force kill any remaining processes
                        wine_procs = subprocess.run(
                            ['pgrep', '-f', r'(wine|\.exe)'],
                            capture_output=True,
                            text=True
                        ).stdout.strip().split('\n')
                        
                        for proc_pid in wine_procs:
                            if proc_pid:
                                try:
                                    pid = int(proc_pid)
                                    print(f"Force killing wine process {pid}")
                                    if self.app.shared_log_window:
                                        self.app.shared_log_window.append_text(f"Force killing wine process {pid}\n")
                                    os.kill(pid, signal.SIGKILL)
                                except (ProcessLookupError, ValueError):
                                    pass
                    except Exception as e:
                        error_msg = f"Error cleaning up wine processes: {e}"
                        print(error_msg)
                        if self.app.shared_log_window:
                            self.app.shared_log_window.append_text(f"ERROR: {error_msg}\n")
                    
                    # Try to stop wineserver as a last resort
                    try:
                        subprocess.run(['wineserver', '-k'], timeout=3)
                    except Exception as e:
                        error_msg = f"Error stopping wineserver: {e}"
                        print(error_msg)
                        if self.app.shared_log_window:
                            self.app.shared_log_window.append_text(f"ERROR: {error_msg}\n")
                        try:
                            subprocess.run(['wineserver', '-k9'], timeout=3)
                        except Exception as e:
                            error_msg = f"Error force stopping wineserver: {e}"
                            print(error_msg)
                            if self.app.shared_log_window:
                                self.app.shared_log_window.append_text(f"ERROR: {error_msg}\n")
                    
                except Exception as e:
                    error_msg = f"Error in process cleanup: {e}"
                    print(error_msg)
                    if self.app.shared_log_window:
                        self.app.shared_log_window.append_text(f"ERROR: {error_msg}\n")
            
            # Clear the process reference
            game.process = None
            
            if self.app.shared_log_window:
                self.app.shared_log_window.append_text(f"=== {game.name} stopped ===\n\n")
            
            # Refresh UI
            GLib.idle_add(self.refresh)
            
        except Exception as e:
            error_msg = f"Error stopping game: {e}"
            print(error_msg)
            if self.app.shared_log_window:
                self.app.shared_log_window.append_text(f"ERROR: {error_msg}\n")
        
        # Always refresh UI
        GLib.idle_add(self.refresh)

    def on_launch_clicked(self, button, game):
        if game.process and game.process.poll() is None:
            # Game is running, stop it
            self.stop_game(game)
        else:
            # Game is not running, launch it
            self.launch_game(game)

    def launch_game(self, game):
        """Launch a game with the configured settings"""
        try:
            # Get game configuration
            flags = self.app.config['flags'].copy()  # Start with global settings as defaults
            for game_config in self.app.config['games']:
                if isinstance(game_config, dict) and game_config.get('path') == game.file_path:
                    # Override with game-specific settings if they exist
                    game_flags = game_config.get('flags', {})
                    flags.update(game_flags)
                    break
            
            # Build command
            command = []
            
            # Add gamemoderun if enabled
            if flags.get('gamemode', False):
                command.extend(['gamemoderun'])
                
            # Add mangohud if enabled
            if flags.get('mangohud', False):
                command.extend(['mangohud'])
            
            # Add umu-run and game path
            command.extend(['umu-run'])
            
            # Add wine flags
            if flags.get('virtual_desktop', False):
                width = flags.get('virtual_desktop_width', 1920)
                height = flags.get('virtual_desktop_height', 1080)
                command.extend(['--virtual-desktop', f'{width}x{height}'])
            
            if flags.get('fullscreen', False):
                command.extend(['--fullscreen'])
            elif flags.get('borderless', False):
                command.extend(['--borderless'])
            
            # Add additional flags if any
            additional_flags = flags.get('additional_flags', '').strip()
            if additional_flags:
                command.extend(additional_flags.split())
            
            # Add the game path
            command.append(game.file_path)
            
            print(f"Launching game with command: {' '.join(command)}")
            
            # Get or create shared log window without showing it
            if not self.app.shared_log_window:
                self.app.create_log_window()
            log_window = self.app.shared_log_window
            
            # Write launch info to log without showing it
            log_window.append_text(f"\n=== Starting {game.name} at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            log_window.append_text(f"Command: {' '.join(command)}\n\n")
            
            def log_output(pipe, prefix=""):
                try:
                    for line in pipe:
                        GLib.idle_add(log_window.append_text, f"{prefix}{line}")
                except Exception as e:
                    print(f"Error logging output: {e}")
            
            # Setup environment
            env = os.environ.copy()
            
            # Set fixed GAMEID for all games
            env['GAMEID'] = 'umu-dauntless'
            
            # Set STORE type (default to egs)
            env['STORE'] = flags.get('store', 'egs').strip()
            
            # Use configured wine prefix, ensure it's never empty
            wineprefix = flags.get('wineprefix', '').strip()
            if not wineprefix:
                wineprefix = os.path.expanduser('~/.wine')
            env['WINEPREFIX'] = wineprefix
            
            # Use configured proton path, ensure it exists
            protonpath = flags.get('protonpath', '').strip()
            if not protonpath:
                protonpath = os.path.expanduser('~/.local/share/Steam/compatibilitytools.d/UMU-Latest')
            
            if not os.path.exists(protonpath):
                error_msg = f"Error: PROTONPATH directory does not exist: {protonpath}"
                print(error_msg)
                if self.app.shared_log_window:
                    self.app.shared_log_window.append_text(f"ERROR: {error_msg}\n")
                self.app.show_error_dialog(error_msg)
                return
                
            env['PROTONPATH'] = protonpath
            
            # Create process group with output logging
            game.process = subprocess.Popen(
                command,
                start_new_session=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1,
                env=env,  # Use our modified environment
                cwd=os.path.dirname(game.file_path)  # Set working directory to game directory
            )
            
            # Start output logging threads
            import threading
            threading.Thread(target=log_output, args=(game.process.stdout,), daemon=True).start()
            threading.Thread(target=log_output, args=(game.process.stderr, "ERROR: "), daemon=True).start()
            
            # Don't show log window by default
            self.app.log_button.remove_css_class('suggested-action')
            
            # Start monitoring the process
            GLib.timeout_add(1000, self.check_game_status, game)
            
            # Refresh UI
            GLib.idle_add(self.refresh)
            
        except Exception as e:
            print(f"Error launching game: {e}")
            game.process = None
            GLib.idle_add(self.refresh)

    def on_remove_clicked(self, button, game):
        # Get the toplevel window
        parent_window = button.get_root()
        
        # Create confirmation dialog
        dialog = Gtk.MessageDialog(
            transient_for=parent_window,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Remove {game.name}?",
            secondary_text="This will only remove the game from the launcher, not from your system."
        )
        
        dialog.connect('response', self.on_remove_confirmed, game)
        dialog.present()

    def on_remove_confirmed(self, dialog, response, game):
        if response == Gtk.ResponseType.YES:
            # Stop the game if it's running
            if game.process and game.process.poll() is None:
                self.stop_game(game)
            
            # Remove from games list
            self.app.games.remove(game)
            
            # Remove from config
            for i, game_config in enumerate(self.app.config.get('games', [])):
                if (isinstance(game_config, dict) and game_config.get('path') == game.file_path) or \
                   (isinstance(game_config, str) and game_config == game.file_path):
                    del self.app.config['games'][i]
                    self.app.save_config()
                    break
            
            # Refresh the list
            self.refresh()
        
        dialog.destroy()

    def on_configure_clicked(self, button, game):
        """Handle configure button click"""
        from .game_config_window import GameConfigWindow
        
        def on_game_updated(updated_game):
            self.refresh()
        
        config_window = GameConfigWindow(
            self.app.window,
            game,
            self.icon_manager,
            on_game_updated
        )
        config_window.present()

    def show_icon_picker(self, game_info):
        """Show icon picker dialog for a game"""
        dialog = Gtk.Dialog(
            title=f"Choose Icon for {game_info.name}",
            transient_for=self.get_root(),
            modal=True
        )
        dialog.set_default_size(400, 500)
        
        # Create icon grid
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        
        grid = Gtk.FlowBox()
        grid.set_valign(Gtk.Align.START)
        grid.set_max_children_per_line(5)
        grid.set_selection_mode(Gtk.SelectionMode.SINGLE)
        grid.set_activate_on_single_click(True)
        
        # Search for icons
        icons = self.icon_manager.search_steamgrid(game_info.name, dialog)
        
        for icon in icons:
            icon_url = icon.get('url')
            if not icon_url:
                continue
                
            # Create icon preview
            image = Gtk.Image()
            image.set_size_request(64, 64)
            
            # Download and show preview
            try:
                response = requests.get(icon_url)
                loader = GdkPixbuf.PixbufLoader()
                loader.write(response.content)
                loader.close()
                pixbuf = loader.get_pixbuf()
                scaled_pixbuf = pixbuf.scale_simple(64, 64, GdkPixbuf.InterpType.BILINEAR)
                image.set_from_pixbuf(scaled_pixbuf)
            except Exception as e:
                print(f"Error loading preview: {e}")
                continue
            
            # Store URL with the image
            image.url = icon_url
            grid.append(image)
        
        scrolled.set_child(grid)
        
        # Add buttons
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Select", Gtk.ResponseType.OK)
        
        # Add content
        content_area = dialog.get_content_area()
        content_area.append(scrolled)
        
        def on_icon_activated(grid, child):
            grid.select_child(child)
        
        grid.connect("child-activated", on_icon_activated)
        
        # Show dialog
        dialog.present()
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            selected = grid.get_selected_children()
            if selected:
                image = selected[0].get_child()
                icon_url = image.url
                if game_info.set_icon(icon_url):
                    self.refresh_game(game_info)
        
        dialog.destroy()
        
    def refresh_game(self, game_info):
        """Refresh a game's display in the list"""
        for row in self.list_box:
            if row.game == game_info:
                # Update icon
                if game_info.icon and os.path.exists(game_info.icon):
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(game_info.icon, 64, 64)
                    row.get_first_child().get_first_child().set_from_pixbuf(pixbuf)
                break

    def add_game(self, name, executable_path, icon_path=None):
        """Add a new game to the list."""
        # Create game with current global settings as defaults
        game = Game(
            name=name,
            executable_path=executable_path,
            icon_path=icon_path,
            flags={
                'fullscreen': self.app.config['flags']['fullscreen'],
                'virtual_desktop': self.app.config['flags']['virtual_desktop'],
                'borderless': self.app.config['flags']['borderless'],
                'gamemode': self.app.config['flags']['gamemode'],
                'mangohud': self.app.config['flags']['mangohud'],
                'additional_flags': self.app.config['flags']['additional_flags'],
                'wineprefix': self.app.config['flags']['wineprefix'],
                'protonpath': self.app.config['flags']['protonpath'],
                'store': self.app.config['flags']['store']
            }
        )
