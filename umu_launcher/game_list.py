import os
import time
import subprocess
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('GdkPixbuf', '2.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk, GLib, Pango, GdkPixbuf, Gio, Gdk, GObject
from pathlib import Path
from .icon_manager import IconManager
from .log_window import LogWindow
from .game_info import GameInfo
import signal
import requests
import logging

logger = logging.getLogger('umu-launcher')

class GameList(Gtk.Box):
    def __init__(self, app, display):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self.display = display
        self.icon_manager = IconManager(app.config.get('steamgriddb_api_key'))
        self.log_windows = {}  # Store log windows for each game
        self.is_grid = False  # Track current layout

        # Enable drag and drop
        drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
        drop_target.connect('drop', self.on_drop)
        drop_target.connect('enter', self.on_drag_enter)
        drop_target.connect('leave', self.on_drag_leave)
        self.add_controller(drop_target)

        # Add drag and drop overlay
        self.overlay = Gtk.Overlay()
        self.append(self.overlay)

        # Create drop indicator
        self.drop_indicator = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.drop_indicator.set_valign(Gtk.Align.CENTER)
        self.drop_indicator.set_halign(Gtk.Align.CENTER)
        self.drop_indicator.set_visible(False)

        # Add icon and label
        icon = Gtk.Image.new_from_icon_name("list-add-symbolic")
        icon.set_pixel_size(64)
        icon.add_css_class("drop-icon")
        self.drop_indicator.append(icon)

        label = Gtk.Label(label="Drop games here to add them")
        label.add_css_class("drop-label")
        self.drop_indicator.append(label)

        self.overlay.set_child(self.drop_indicator)

        # Create scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        self.overlay.set_child(scrolled)

        # Create flow box for games
        self.game_box = Gtk.FlowBox()
        self.game_box.set_valign(Gtk.Align.START)
        self.game_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.game_box.set_homogeneous(True)
        self.game_box.set_sort_func(self.sort_games)

        # Enable reordering
        self.game_box.set_activate_on_single_click(False)
        
        # Set initial list view
        self.game_box.set_min_children_per_line(1)
        self.game_box.set_max_children_per_line(1)

        scrolled.set_child(self.game_box)

        # Add styles
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            .game-list { 
                padding: 8px;
                background: transparent;
            }
            .game-row {
                padding: 8px;
                margin: 4px;
                border-radius: 8px;
                background: alpha(@theme_fg_color, 0.1);
                transition: all 200ms ease;
            }
            .game-row:hover {
                background: alpha(@theme_fg_color, 0.15);
                transform: translateY(-1px);
                box-shadow: 0 2px 4px alpha(black, 0.2);
            }
            .drop-icon {
                color: @theme_fg_color;
                opacity: 0.5;
            }
            .drop-label {
                font-size: 18px;
                font-weight: bold;
                opacity: 0.7;
                color: @theme_fg_color;
            }
            .drop-highlight {
                border: 2px dashed alpha(@theme_fg_color, 0.3);
                border-radius: 12px;
                background: alpha(@theme_fg_color, 0.05);
            }
            .game-icon {
                border-radius: 8px;
                background: alpha(@theme_fg_color, 0.1);
            }
            .game-title {
                font-weight: bold;
                font-size: 14px;
                color: @theme_fg_color;
            }
            .game-path {
                font-size: 12px;
                opacity: 0.7;
                color: @theme_fg_color;
            }
            .game-button {
                padding: 6px;
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
            .dragging {
                opacity: 0.5;
            }
            .drop-target {
                border: 2px dashed alpha(@theme_fg_color, 0.3);
                border-radius: 12px;
                background: alpha(@theme_fg_color, 0.05);
            }
        """)
        Gtk.StyleContext.add_provider_for_display(
            display,
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    
    def create_game_widget(self, game):
        """Create a widget for a game"""
        # Create main box for game
        game_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        game_box.add_css_class('game-row')
        game_box.set_margin_start(4)
        game_box.set_margin_end(4)
        game_box.set_margin_top(4)
        game_box.set_margin_bottom(4)

        # Store the game reference
        game_box.game = game
        
        # Enable drag source
        drag_source = Gtk.DragSource.new()
        drag_source.set_actions(Gdk.DragAction.MOVE)
        drag_source.connect('prepare', self.on_drag_prepare, game)
        drag_source.connect('drag-begin', self.on_drag_begin, game_box)
        drag_source.connect('drag-end', self.on_drag_end, game_box)
        game_box.add_controller(drag_source)

        # Enable drop target for reordering
        drop_target = Gtk.DropTarget.new(GObject.TYPE_PYOBJECT, Gdk.DragAction.MOVE)
        drop_target.connect('drop', self.on_reorder_drop, game)
        drop_target.connect('enter', self.on_reorder_enter, game_box)
        drop_target.connect('leave', self.on_reorder_leave, game_box)
        game_box.add_controller(drop_target)

        if self.is_grid:
            # Grid mode: Vertical layout
            left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            left_box.set_hexpand(True)
            
            # Add game icon
            icon = Gtk.Image()
            icon.add_css_class('game-icon')
            icon.set_pixel_size(96)
            
            # Load icon
            if game.icon and os.path.exists(game.icon):
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(game.icon, 96, 96)
                    icon.set_from_pixbuf(pixbuf)
                except Exception as e:
                    logger.error(f"Error loading icon: {e}")
                    icon.set_from_icon_name("application-x-executable")
            else:
                icon.set_from_icon_name("application-x-executable")
            
            icon_box = Gtk.Box()
            icon_box.set_halign(Gtk.Align.CENTER)
            icon_box.append(icon)
            left_box.append(icon_box)
            
            # Add game name
            name_label = Gtk.Label(label=game.name)
            name_label.set_wrap(True)
            name_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
            name_label.set_max_width_chars(20)
            name_label.set_justify(Gtk.Justification.CENTER)
            name_label.set_halign(Gtk.Align.CENTER)
            name_label.add_css_class('game-title')
            left_box.append(name_label)
        else:
            # List mode: Original horizontal layout
            left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            left_box.set_hexpand(True)
            
            # Create info box for icon and name
            info_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
            
            # Add game icon
            icon = Gtk.Image()
            icon.add_css_class('game-icon')
            icon.set_pixel_size(64)
            
            # Load icon
            if game.icon and os.path.exists(game.icon):
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(game.icon, 64, 64)
                    icon.set_from_pixbuf(pixbuf)
                except Exception as e:
                    logger.error(f"Error loading icon: {e}")
                    icon.set_from_icon_name("application-x-executable")
            else:
                icon.set_from_icon_name("application-x-executable")
            
            info_box.append(icon)
            
            # Create name and path box
            text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            
            # Add game name
            name_label = Gtk.Label(label=game.name)
            name_label.set_halign(Gtk.Align.START)
            name_label.add_css_class('game-title')
            text_box.append(name_label)
            
            # Add game path
            path_label = Gtk.Label(label=game.file_path)
            path_label.set_halign(Gtk.Align.START)
            path_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
            path_label.add_css_class("game-path")
            text_box.append(path_label)
            
            info_box.append(text_box)
            left_box.append(info_box)
        
        # Create box for buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        button_box.set_halign(Gtk.Align.CENTER if self.is_grid else Gtk.Align.END)
        
        # Add play button
        play_button = Gtk.Button()
        if game.process and game.process.poll() is None:
            play_button.set_icon_name('media-playback-stop-symbolic')
            play_button.set_tooltip_text('Stop Game')
            play_button.add_css_class('destructive-action')
        else:
            play_button.set_icon_name('media-playback-start-symbolic')
            play_button.set_tooltip_text('Play Game')
            play_button.add_css_class('suggested-action')
        play_button.add_css_class('game-button')
        play_button.connect('clicked', lambda b: self.on_launch_clicked(b, game))
        button_box.append(play_button)
        
        # Add configure button
        config_button = Gtk.Button()
        config_button.set_icon_name('emblem-system-symbolic')
        config_button.add_css_class('game-button')
        config_button.add_css_class('configure')
        config_button.set_tooltip_text('Game Settings')
        config_button.connect('clicked', lambda b: self.on_configure_clicked(b, game))
        button_box.append(config_button)
        
        # Add remove button
        remove_button = Gtk.Button()
        remove_button.set_icon_name('user-trash-symbolic')
        remove_button.add_css_class('game-button')
        remove_button.add_css_class('destructive-action')
        remove_button.set_tooltip_text('Remove Game')
        remove_button.connect('clicked', lambda b: self.on_remove_clicked(b, game))
        button_box.append(remove_button)
        
        # Add boxes to main box based on layout
        if self.is_grid:
            # Grid mode: Vertical layout with buttons under icon/name
            left_box.append(button_box)
            game_box.append(left_box)
        else:
            # List mode: Horizontal layout with buttons on right
            game_box.append(left_box)
            button_box.set_valign(Gtk.Align.CENTER)
            game_box.append(button_box)
        
        return game_box

    def refresh(self):
        """Refresh the game list"""
        # Remove all existing children
        while True:
            child = self.game_box.get_first_child()
            if child is None:
                break
            self.game_box.remove(child)
        
        # Add games back with current layout
        for game in self.app.games:
            game_widget = self.create_game_widget(game)
            flow_child = Gtk.FlowBoxChild()
            flow_child.set_child(game_widget)
            self.game_box.append(flow_child)
            
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
            
            flow_child = Gtk.FlowBoxChild()
            flow_child.set_child(empty_box)
            self.game_box.append(flow_child)
    
    def check_game_status(self, game):
        """Check if a game is still running and update UI accordingly"""
        try:
            # Check if process has exited
            if game.process and game.process.poll() is not None:
                # Game has stopped
                logger.info(f"Game {game.name} has stopped")
                # Add stop message to log
                if game in self.log_windows:
                    GLib.idle_add(self.log_windows[game].append_text, f"\n=== Game stopped at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                # Clean up any remaining wine processes
                self.stop_game(game)
                return False  # Stop monitoring
            return True  # Continue monitoring
        except Exception as e:
            logger.error(f"Error checking game status: {e}")
            return False  # Stop monitoring on error

    def stop_game(self, game):
        """Stop a running game and its associated processes"""
        try:
            logger.info(f"Stopping game {game.name}")
            
            # Log to shared log window if it exists
            if self.app.shared_log_window:
                self.app.shared_log_window.append_text(f"\n=== Stopping {game.name} at {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            
            if game.process and game.process.poll() is None:
                try:
                    # First try to terminate the main process group
                    pid = game.process.pid
                    logger.info(f"Sending SIGTERM to process group {pid}")
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
                                    logger.info(f"Terminating wine process {pid}")
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
                                    logger.info(f"Force killing wine process {pid}")
                                    if self.app.shared_log_window:
                                        self.app.shared_log_window.append_text(f"Force killing wine process {pid}\n")
                                    os.kill(pid, signal.SIGKILL)
                                except (ProcessLookupError, ValueError):
                                    pass
                    except Exception as e:
                        error_msg = f"Error cleaning up wine processes: {e}"
                        logger.error(error_msg)
                        if self.app.shared_log_window:
                            self.app.shared_log_window.append_text(f"ERROR: {error_msg}\n")
                    
                    # Try to stop wineserver as a last resort
                    try:
                        subprocess.run(['wineserver', '-k'], timeout=3)
                    except Exception as e:
                        error_msg = f"Error stopping wineserver: {e}"
                        logger.error(error_msg)
                        if self.app.shared_log_window:
                            self.app.shared_log_window.append_text(f"ERROR: {error_msg}\n")
                        try:
                            subprocess.run(['wineserver', '-k9'], timeout=3)
                        except Exception as e:
                            error_msg = f"Error force stopping wineserver: {e}"
                            logger.error(error_msg)
                            if self.app.shared_log_window:
                                self.app.shared_log_window.append_text(f"ERROR: {error_msg}\n")
                    
                except Exception as e:
                    error_msg = f"Error in process cleanup: {e}"
                    logger.error(error_msg)
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
            logger.error(error_msg)
            if self.app.shared_log_window:
                self.app.shared_log_window.append_text(f"ERROR: {error_msg}\n")
        
        # Always refresh UI
        GLib.idle_add(self.refresh)

    def on_launch_clicked(self, button, game):
        if game.process and game.process.poll() is None:
            # Game is running, stop it
            button.set_icon_name('media-playback-start-symbolic')
            button.set_tooltip_text('Play Game')
            button.remove_css_class('destructive-action')
            button.add_css_class('suggested-action')
            self.stop_game(game)
        else:
            # Game is not running, launch it
            button.set_icon_name('media-playback-stop-symbolic')
            button.set_tooltip_text('Stop Game')
            button.remove_css_class('suggested-action')
            button.add_css_class('destructive-action')
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
            
            # Add umu-run
            command.extend(['umu-run'])
            
            # Add the game path
            command.append(game.file_path)
            
            # Add additional flags if any
            additional_flags = flags.get('additional_flags', '').strip()
            if additional_flags:
                command.extend(additional_flags.split())
            
            logger.info(f"Launching game with command: {' '.join(command)}")
            
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
                    logger.error(f"Error logging output: {e}")
            
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
                logger.error(error_msg)
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
            logger.error(f"Error launching game: {e}")
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
        
        def on_game_updated(updated_game, confirmed=True):
            # Only refresh if configuration was confirmed
            if confirmed:
                self.refresh()
        
        config_window = GameConfigWindow(
            self.app.window,
            game,
            self.icon_manager,
            on_game_updated
        )
        config_window.set_transient_for(self.get_root())
        config_window.present()

    def toggle_layout(self):
        """Toggle between list and grid layout"""
        self.is_grid = not self.is_grid
        
        if self.is_grid:
            # Grid view: 3 items per line
            self.game_box.set_min_children_per_line(3)
            self.game_box.set_max_children_per_line(3)
        else:
            # List view: 1 item per line
            self.game_box.set_min_children_per_line(1)
            self.game_box.set_max_children_per_line(1)
            
        # Force re-layout
        self.refresh()
        return self.is_grid

    def on_drop(self, drop_target, value, x, y):
        """Handle file drops"""
        if not isinstance(value, Gio.File):
            return False

        file_path = value.get_path()
        if not file_path:
            return False

        # Check if it's a Windows executable
        if not file_path.lower().endswith('.exe'):
            self.app.show_error_dialog("Only Windows .exe files can be added")
            return False

        # Add the game
        game_info = GameInfo(file_path)
        self.app.games.append(game_info)
        
        # Add to config
        if 'games' not in self.app.config:
            self.app.config['games'] = []
        self.app.config['games'].append({'path': file_path})
        self.app.save_config()

        # Refresh the list
        self.refresh()
        return True

    def on_drag_enter(self, drop_target, x, y):
        """Show drop indicator when dragging over"""
        self.drop_indicator.set_visible(True)
        self.add_css_class('drop-highlight')
        return Gdk.DragAction.COPY

    def on_drag_leave(self, drop_target):
        """Hide drop indicator when dragging out"""
        self.drop_indicator.set_visible(False)
        self.remove_css_class('drop-highlight')

    def on_drag_prepare(self, drag_source, x, y, game):
        """Prepare the drag operation"""
        return Gdk.ContentProvider.new_for_value(game)

    def on_drag_begin(self, drag_source, drag, game_box):
        """Handle start of drag"""
        game_box.add_css_class('dragging')
        
    def on_drag_end(self, drag_source, drag, drag_cancel, game_box):
        """Handle end of drag"""
        game_box.remove_css_class('dragging')

    def on_reorder_enter(self, drop_target, x, y, game_box):
        """Handle drag enter for reordering"""
        game_box.add_css_class('drop-target')
        return Gdk.DragAction.MOVE

    def on_reorder_leave(self, drop_target, game_box):
        """Handle drag leave for reordering"""
        game_box.remove_css_class('drop-target')

    def on_reorder_drop(self, drop_target, value, x, y, target_game):
        """Handle drop for reordering"""
        if not isinstance(value, GameInfo):
            return False

        source_game = value
        if source_game == target_game:
            return False

        # Get the positions
        source_idx = self.app.games.index(source_game)
        target_idx = self.app.games.index(target_game)

        # Reorder in the games list
        self.app.games.pop(source_idx)
        self.app.games.insert(target_idx, source_game)

        # Update config
        if 'games' in self.app.config:
            source_config = self.app.config['games'][source_idx]
            self.app.config['games'].pop(source_idx)
            self.app.config['games'].insert(target_idx, source_config)
            self.app.save_config()

        # Refresh the list
        self.refresh()
        return True

    def sort_games(self, child1, child2, user_data=None):
        """Sort function for the flow box to maintain order"""
        game1 = child1.get_child().game
        game2 = child2.get_child().game
        idx1 = self.app.games.index(game1)
        idx2 = self.app.games.index(game2)
        return idx1 - idx2
