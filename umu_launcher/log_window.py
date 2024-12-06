import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib, Gdk, Gio
import os
import re

class LogWindow(Gtk.Window):
    # ANSI color code to GTK color mapping
    ANSI_COLORS = {
        '30': '#000000',  # Black
        '31': '#C62828',  # Red
        '32': '#2E7D32',  # Green
        '33': '#F57C00',  # Yellow
        '34': '#1976D2',  # Blue
        '35': '#7B1FA2',  # Magenta
        '36': '#0097A7',  # Cyan
        '37': '#757575',  # White
        '90': '#616161',  # Bright Black (Gray)
        '91': '#EF5350',  # Bright Red
        '92': '#4CAF50',  # Bright Green
        '93': '#FFA726',  # Bright Yellow
        '94': '#42A5F5',  # Bright Blue
        '95': '#AB47BC',  # Bright Magenta
        '96': '#26C6DA',  # Bright Cyan
        '97': '#FFFFFF',  # Bright White
    }

    def __init__(self, parent, width=600, height=300, position='bottom'):
        """
        Initialize the log window
        
        Args:
            parent: Parent window
            width: Window width in pixels
            height: Window height in pixels
            position: Window position ('bottom', 'right', 'left')
        """
        super().__init__(
            transient_for=parent,
            modal=False,
            decorated=False
        )
        
        # Store configuration
        self.window_width = width
        self.window_height = height
        self.window_position = position
        
        # Set window properties
        self.set_default_size(width, height)
        self.set_resizable(False)
        
        # Create main box
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.main_box.set_margin_start(12)
        self.main_box.set_margin_end(12)
        self.main_box.set_margin_top(12)
        self.main_box.set_margin_bottom(12)
        
        # Add header
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        # Make header draggable
        drag_area = Gtk.WindowHandle()
        drag_area.set_child(header_box)
        self.main_box.append(drag_area)
        
        # Add title
        self.title_label = Gtk.Label(label="Game Log")
        self.title_label.add_css_class("title")
        header_box.append(self.title_label)
        
        # Add spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        header_box.append(spacer)
        
        # Add minimize button
        minimize_button = Gtk.Button()
        minimize_button.set_icon_name("go-down-symbolic")
        minimize_button.connect("clicked", self.on_minimize_clicked)
        header_box.append(minimize_button)
        
        # Add scrolled window for log
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        
        # Add text view for log
        self.text_view = Gtk.TextView()
        self.text_view.set_editable(False)
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.text_view.set_monospace(True)
        self.text_buffer = self.text_view.get_buffer()
        
        # Create text tags for different log levels and ANSI colors
        self.text_buffer.create_tag("info", foreground="#2E7D32")  # Dark green
        self.text_buffer.create_tag("warning", foreground="#F57C00")  # Orange
        self.text_buffer.create_tag("error", foreground="#C62828")  # Dark red
        self.text_buffer.create_tag("debug", foreground="#1976D2")  # Blue
        self.text_buffer.create_tag("timestamp", foreground="#616161", scale=0.9)  # Gray, slightly smaller
        
        # Create tags for ANSI colors
        for code, color in self.ANSI_COLORS.items():
            self.text_buffer.create_tag(f"ansi_{code}", foreground=color)
        
        # Create tag for bold text
        self.text_buffer.create_tag("bold", weight=700)  # Pango.Weight.BOLD equivalent
        
        scrolled.set_child(self.text_view)
        self.main_box.append(scrolled)
        
        self.set_child(self.main_box)
        
        # Add CSS styling based on position
        border_radius = "12px"
        if position == 'right':
            border_css = """
                window {
                    background-color: @theme_bg_color;
                    border-top: 1px solid @borders;
                    border-left: 1px solid @borders;
                    border-bottom: 1px solid @borders;
                    border-top-left-radius: %s;
                    border-bottom-left-radius: %s;
                }
                .title {
                    font-weight: bold;
                    font-size: 16px;
                }
                textview {
                    font-family: "JetBrains Mono", monospace;
                    padding: 8px;
                    background-color: @theme_base_color;
                    color: @theme_fg_color;
                }
                textview text {
                    background-color: @theme_base_color;
                }
                scrolledwindow {
                    border: 1px solid alpha(@borders, 0.5);
                    border-radius: 6px;
                }
            """ % (border_radius, border_radius)
        elif position == 'left':
            border_css = """
                window {
                    background-color: @theme_bg_color;
                    border-top: 1px solid @borders;
                    border-right: 1px solid @borders;
                    border-bottom: 1px solid @borders;
                    border-top-right-radius: %s;
                    border-bottom-right-radius: %s;
                }
                .title {
                    font-weight: bold;
                    font-size: 16px;
                }
                textview {
                    font-family: "JetBrains Mono", monospace;
                    padding: 8px;
                    background-color: @theme_base_color;
                    color: @theme_fg_color;
                }
                textview text {
                    background-color: @theme_base_color;
                }
                scrolledwindow {
                    border: 1px solid alpha(@borders, 0.5);
                    border-radius: 6px;
                }
            """ % (border_radius, border_radius)
        else:  # bottom
            border_css = """
                window {
                    background-color: @theme_bg_color;
                    border-top: 1px solid @borders;
                    border-left: 1px solid @borders;
                    border-right: 1px solid @borders;
                    border-top-left-radius: %s;
                    border-top-right-radius: %s;
                }
                .title {
                    font-weight: bold;
                    font-size: 16px;
                }
                textview {
                    font-family: "JetBrains Mono", monospace;
                    padding: 8px;
                    background-color: @theme_base_color;
                    color: @theme_fg_color;
                }
                textview text {
                    background-color: @theme_base_color;
                }
                scrolledwindow {
                    border: 1px solid alpha(@borders, 0.5);
                    border-radius: 6px;
                }
            """ % (border_radius, border_radius)
        
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(border_css.encode())
        
        self.get_style_context().add_provider(
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        
        # Initialize state
        self.is_minimized = True
        self.animation_duration = 250  # ms
        self.animation_start_time = 0
        
        # Set up window positioning
        self.set_hide_on_close(True)
    
    def get_parent_bounds(self):
        """Get parent window bounds"""
        parent = self.get_transient_for()
        if not parent:
            return None
            
        native = parent.get_native()
        if not native:
            return None
            
        bounds = native.get_bounds()
        if not bounds:
            return None
            
        return bounds
    
    def show_with_animation(self):
        """Show the window with a slide animation"""
        if not self.is_visible():
            # Get parent bounds
            bounds = self.get_parent_bounds()
            if not bounds:
                return
            
            # Calculate initial position
            if self.window_position == 'right':
                x = bounds.width
                y = (bounds.height - self.window_height) // 2
            elif self.window_position == 'left':
                x = -self.window_width
                y = (bounds.height - self.window_height) // 2
            else:  # bottom
                x = (bounds.width - self.window_width) // 2
                y = bounds.height
            
            # Set initial position and show window
            self.set_default_size(self.window_width, 0)
            
            # Position relative to parent
            self.set_transient_for(self.get_transient_for())
            self.present()
            
            # Start animation
            self.is_minimized = False
            self.animation_start_time = GLib.get_monotonic_time()
            self.add_tick_callback(self.animate_show)
    
    def hide_with_animation(self):
        """Hide the window with a slide animation"""
        if self.is_visible():
            # Start animation
            self.is_minimized = True
            self.animation_start_time = GLib.get_monotonic_time()
            self.add_tick_callback(self.animate_hide)
    
    def animate_show(self, widget, frame_clock):
        """Animate showing the window"""
        now = GLib.get_monotonic_time()
        progress = min(1.0, (now - self.animation_start_time) / (self.animation_duration * 1000))
        
        if progress < 1.0:
            if self.window_position in ('left', 'right'):
                width = int(self.window_width * progress)
                self.set_default_size(width, self.window_height)
            else:  # bottom
                height = int(self.window_height * progress)
                self.set_default_size(self.window_width, height)
            return True
        else:
            self.set_default_size(self.window_width, self.window_height)
            return False
    
    def animate_hide(self, widget, frame_clock):
        """Animate hiding the window"""
        now = GLib.get_monotonic_time()
        progress = min(1.0, (now - self.animation_start_time) / (self.animation_duration * 1000))
        
        if progress < 1.0:
            if self.window_position in ('left', 'right'):
                width = int(self.window_width * (1 - progress))
                self.set_default_size(width, self.window_height)
            else:  # bottom
                height = int(self.window_height * (1 - progress))
                self.set_default_size(self.window_width, height)
            return True
        else:
            self.hide()
            return False
    
    def on_minimize_clicked(self, button):
        """Handle minimize button click"""
        self.hide_with_animation()
    
    def parse_ansi_codes(self, text):
        """Parse ANSI escape codes and return a list of (text, tags) tuples"""
        result = []
        current_tags = set()
        
        # Regular expression for ANSI escape codes, including escape character
        ansi_pattern = re.compile(r'(?:\x1B|\[)(?:\[[0-9;]*[@-~]|\[.*?[@-~]|[0-9;]*[mK])')
        
        # Split the text into parts
        last_end = 0
        for match in ansi_pattern.finditer(text):
            # Add any text before the ANSI code
            if match.start() > last_end:
                result.append((text[last_end:match.start()], list(current_tags)))
            
            # Process the ANSI code
            code = match.group()
            if 'm' in code:  # Color/style code
                codes = code.strip('[]m').split(';')
                for c in codes:
                    if c == '0' or not c:  # Reset
                        current_tags.clear()
                    elif c == '1':  # Bold
                        current_tags.add('bold')
                    elif c in self.ANSI_COLORS:  # Color code
                        # Remove any existing color tags
                        current_tags = {tag for tag in current_tags if not tag.startswith('ansi_')}
                        current_tags.add(f'ansi_{c}')
            
            last_end = match.end()
        
        # Add any remaining text
        if last_end < len(text):
            result.append((text[last_end:], list(current_tags)))
        
        return result

    def append_text(self, text, level="info"):
        """
        Append text to the log with specified level
        
        Args:
            text: Text to append
            level: Log level (info, warning, error, debug)
        """
        end_iter = self.text_buffer.get_end_iter()
        
        # Clean the text of any null characters or other problematic control chars
        text = ''.join(char for char in text if char >= ' ' or char in '\n\r\t')
        
        # Extract timestamp if present in the format [HH:MM:SS]
        timestamp_match = re.match(r'^\[(\d{2}:\d{2}:\d{2})\]\s*', text)
        if timestamp_match:
            timestamp = timestamp_match.group(0)
            text = text[len(timestamp):]
            self.text_buffer.insert_with_tags_by_name(end_iter, timestamp, "timestamp")
        else:
            # Add current timestamp if none present
            timestamp = GLib.DateTime.new_now_local().format("[%H:%M:%S] ")
            self.text_buffer.insert_with_tags_by_name(end_iter, timestamp, "timestamp")
        
        # Parse and apply ANSI color codes
        parts = self.parse_ansi_codes(text)
        for text_part, tags in parts:
            if tags:
                self.text_buffer.insert_with_tags_by_name(end_iter, text_part, *tags)
            else:
                # If no ANSI tags, use the log level tag
                if level in ["info", "warning", "error", "debug"]:
                    self.text_buffer.insert_with_tags_by_name(end_iter, text_part, level)
                else:
                    self.text_buffer.insert(end_iter, text_part)
        
        # Add newline if not present
        if not text.endswith("\n"):
            self.text_buffer.insert(end_iter, "\n")
        
        # Scroll to bottom
        mark = self.text_buffer.create_mark(None, end_iter, False)
        self.text_view.scroll_mark_onscreen(mark)
        self.text_buffer.delete_mark(mark)
